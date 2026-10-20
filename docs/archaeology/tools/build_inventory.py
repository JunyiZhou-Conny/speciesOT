"""Inventory every experiment-bearing file in one or more git checkouts.

Run-level results (trained models on FASRC) are indexed separately by
`scripts/build_experiments_inventory.py` and `./hub list`. This script covers
what those miss: notebooks, specs, scripts, sbatch files, and research logs,
including the ones in Josh's repository.

For each tracked file it records git history (first/last commit date and
author), size, a content hash for spotting byte-identical copies across
repositories, and, for notebooks, the title, cell counts, imports, and the
`.h5ad` files it references.

Read-only: the only file written is the CSV given by --out.

`inventory.csv` was built from the repo root with fresh clones of the other
repositories under $SRC:

    python docs/archaeology/tools/build_inventory.py \
        --repo conny=. \
        --repo josh_main=$SRC/speciesOT-josh@origin/main \
        --repo josh_cellot=$SRC/speciesOT-josh@origin/cellot \
        --repo josh_pkg=$SRC/speciesOT-josh@origin/scgen-model-impl \
        --repo autoresearch=$SRC/scgen-cellot-autoresearch \
        --repo ablation=$SRC/scgen-cellot-ablation \
        --repo ai_package=$SRC/speciesost-package@origin/src \
        --out docs/archaeology/inventory.csv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

NOTEBOOK = ".ipynb"
SCRIPT_SUFFIXES = {".py", ".sh", ".sbatch", ".slurm"}
CONFIG_SUFFIXES = {".yaml", ".yml"}
LOG_DIRS = ("logs/",)

# Imports worth surfacing: they say which model stack a notebook used.
TRACKED_IMPORTS = {
    "scgen", "scvi", "cellot", "ot", "ott", "torch", "tensorflow", "keras",
    "scanpy", "anndata", "celltypist", "pertpy", "jax", "sklearn", "otdd",
    "speciesot", "speciesot_helpers", "speciesot_simulation_helpers",
    "pytorch_helpers",
}
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w]*)", re.M)
H5AD_RE = re.compile(r"[\w./~${}-]*\.h5ad")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, capture_output=True, text=True,
    ).stdout


def file_history(repo: Path, ref: str) -> dict[str, list[tuple[str, str]]]:
    """Map path -> [(date, author), ...] newest first, from one `git log` pass."""
    history: dict[str, list[tuple[str, str]]] = defaultdict(list)
    out = git(repo, "log", "--name-only", "--format=@@%ad|%an", "--date=short", ref)
    date = author = ""
    for line in out.splitlines():
        if line.startswith("@@"):
            date, author = line[2:].split("|", 1)
        elif line.strip():
            history[line.strip()].append((date, author))
    return history


def classify(path: str) -> str | None:
    p = Path(path)
    if p.suffix == NOTEBOOK:
        return "notebook"
    if path.startswith(LOG_DIRS) and p.suffix in {".txt", ".md"}:
        return "log"
    if p.suffix in CONFIG_SUFFIXES and not path.startswith(".") and "/.obsidian/" not in path:
        return "config"
    if p.suffix in SCRIPT_SUFFIXES:
        return "script"
    return None


def notebook_facts(raw: bytes) -> dict[str, object]:
    try:
        nb = json.loads(raw)
    except ValueError:
        return {"title": "<unreadable notebook>"}
    cells = nb.get("cells", [])
    title = ""
    for cell in cells:
        if cell.get("cell_type") == "markdown":
            text = "".join(cell.get("source", [])).strip()
            if text:
                title = text.splitlines()[0].lstrip("# ").strip()[:120]
                break
    code = ["".join(c.get("source", [])) for c in cells if c.get("cell_type") == "code"]
    joined = "\n".join(code)
    imports = sorted({m for m in IMPORT_RE.findall(joined) if m in TRACKED_IMPORTS})
    h5ads = sorted({Path(m).name for m in H5AD_RE.findall(joined)})
    with_output = sum(1 for c in cells if c.get("cell_type") == "code" and c.get("outputs"))
    return {
        "title": title,
        "n_code_cells": len(code),
        "n_cells_with_output": with_output,
        "imports": " ".join(imports),
        "h5ad_refs": " ".join(h5ads[:12]) + (" ..." if len(h5ads) > 12 else ""),
    }


def inventory(name: str, repo: Path, ref: str) -> list[dict[str, object]]:
    history = file_history(repo, ref)
    sha = git(repo, "rev-parse", "--short", ref).strip()
    rows = []
    for path in git(repo, "ls-tree", "-r", "--name-only", ref).splitlines():
        kind = classify(path)
        if kind is None:
            continue
        # Read the committed blob, not the working tree, so uncommitted
        # edits never leak into the inventory.
        raw = subprocess.run(
            ["git", "-C", str(repo), "show", f"{ref}:{path}"],
            check=True, capture_output=True,
        ).stdout
        commits = history.get(path, [])
        row: dict[str, object] = {
            "repo": name,
            "ref": f"{ref}@{sha}",
            "path": path,
            "kind": kind,
            "size_bytes": len(raw),
            "sha12": hashlib.sha256(raw).hexdigest()[:12],
            "first_date": commits[-1][0] if commits else "",
            "first_author": commits[-1][1] if commits else "",
            "last_date": commits[0][0] if commits else "",
            "last_author": commits[0][1] if commits else "",
            "n_commits": len(commits),
        }
        if kind == "notebook":
            row.update(notebook_facts(raw))
        rows.append(row)
    return rows


def mark_duplicates(rows: list[dict[str, object]]) -> None:
    by_hash: dict[object, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_hash[row["sha12"]].append(row)
    for group in by_hash.values():
        for row in group:
            others = [f"{o['repo']}:{o['path']}" for o in group if o is not row]
            row["identical_copies"] = " ".join(others)


COLUMNS = [
    "repo", "ref", "path", "kind", "title", "first_date", "first_author",
    "last_date", "last_author", "n_commits", "size_bytes", "sha12",
    "identical_copies", "n_code_cells", "n_cells_with_output", "imports",
    "h5ad_refs",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repo", action="append", required=True,
                        help="name=path[@ref] of a git checkout (ref defaults "
                             "to HEAD); repeat for each repo or branch")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    for spec in args.repo:
        name, _, location = spec.partition("=")
        path, _, ref = location.partition("@")
        rows.extend(inventory(name, Path(path).resolve(), ref or "HEAD"))
    mark_duplicates(rows)
    rows.sort(key=lambda r: (str(r["repo"]), str(r["kind"]), str(r["path"])))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    counts = defaultdict(int)
    for row in rows:
        counts[(row["repo"], row["kind"])] += 1
    for (repo, kind), n in sorted(counts.items()):
        print(f"{repo:>12} {kind:<9} {n}")
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
