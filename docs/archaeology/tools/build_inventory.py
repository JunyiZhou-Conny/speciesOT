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
        --repo conny=.@origin/main \
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

# Which experiment-family page (docs/archaeology/experiments/) covers a file.
# First match wins; patterns are matched against "<repo>:<path>".
FAMILY_RULES = [
    (r"^(autoresearch):", "F13"),
    (r"^(ablation):", "F12"),
    (r"^(ai_package):", "F18"),
    (r"(^|/|:)src/speciesot/|e24_src_example|example_debugging", "F18"),
    (r"(^|/|:)(tabula_eda|tabula_make_samples|intraspecies_vs_interspecies_dists"
     r"|pca_sinkhorn_optimization)\.ipynb|/phylogeny/|:phylogeny/"
     r"|e[5-8]_[a-z_]+\.ipynb|speciesot_(simulation_)?helpers\.py|pytorch_helpers\.py", "F01"),
    (r"perturbOT_tutorial|(^|/|:)e(1|3|4|12|21)_[a-z_0-9]+\.ipynb", "F02"),
    (r"(^|/|:)e(2|9|10|11|13)_[a-z_]+\.ipynb", "F03"),
    (r"(^|/|:)e(14|15|16|17|19)_[a-z_]+\.ipynb", "F04"),
    (r"(^|/|:)tb/|(^|/|:)e(20|22|23)_|analysis/(16|16\.[1-4]|17)_"
     r"|plot_bcg_paper_figures|score_bcg_and_plot", "F17"),
    (r"analysis/(archive/)?(01\.2|01\.3|08\.1|09|10|11)_", "F07"),
    (r"analysis/(archive/)?(01\.1|01\.4|01\.5|13|14)_|hvg_flavor", "F08"),
    (r"analysis/(archive/)?15_|atlas_full_|atlas_uncapped_|mixhvg_|predict_new_input"
     r"|eval_external_target|bake_model_artifacts|h5ad_to_v07|generate_atlas_full_configs"
     r"|verify_offline_bundle|uncapped_chain|research_log_2026-07-30", "F16"),
    (r"analysis/(19|20|21|21\.1|21\.2|22)_|umap_learn_and_investigate|m1_atlas_ood_outlier|specs/(m1_modern|m2_baseline"
     r"|atlas_cd8_uncapped)|scripts/(extended_metrics|decoded_frame_metrics|mmd_floor"
     r"|ae_identity_metrics|dump_eval_clouds)|research_log_2026-06-09", "F10"),
    (r"analysis/(23|24)_|paper_crossspecies|explore_LPS_dataset|research_log_2026-06-1[34]", "F11"),
    (r"lps_icnn_ae_study|research_log_2026-07-20", "F13"),
    (r"lps_scgen_ae_followup|e3_devar_confirmation|research_log_2026-07-2[37]", "F15"),
    (r"atlas-paper-vae/|atlas_paper_vae|scgen-cellot-unbalanced/|agent_plans_2026-07-21", "F14"),
    (r"research_log_2026-03-15", "F05"),
    (r"(^|/|:)e18_|speciesOT/visualization/", "F06"),
    (r"analysis/|research_log_2026-0(3-2|3-3|4-0[1-7])|baseline/|biomart", "F06"),
    (r"research_log_2026-04-(08|13|20)|generate_data_space_eval|generate_toggle_configs", "F07"),
    (r"research_log_2026-05-04", "F08"),
    (r"speciesOT/hub/|(^|:)hub$|build_experiments_inventory|\.cursor/|(^|:)scripts/"
     r"|:speciesOT/__init__\.py$", "F09"),
    (r"cellot/cellot_gpu/", "vendored CellOT"),
]


def family_of(repo: str, path: str) -> str:
    key = f"{repo}:{path}"
    for pattern, family in FAMILY_RULES:
        if re.search(pattern, key):
            return family
    return ""


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
            "family": family_of(name, path),
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
    "repo", "ref", "path", "kind", "family", "title", "first_date", "first_author",
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
    unassigned = [f"{r['repo']}:{r['path']}" for r in rows if not r["family"]]
    print(f"wrote {len(rows)} rows to {args.out}; {len(unassigned)} without a family")
    for item in unassigned:
        print(f"  no family: {item}")


if __name__ == "__main__":
    main()
