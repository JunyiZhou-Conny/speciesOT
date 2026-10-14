#!/usr/bin/env python3
"""Check path and line citations in docs/learning.

A citation is a backtick token that is a repo path, a josh: path, or a zip:
member, optionally with :start or :start-end. Prose tokens are ignored.
The script also requires every notebook in this repo to appear in the
archaeology report.
"""

import os
import re
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LEARNING = REPO / "docs" / "learning"
REPORT = LEARNING / "experiment-archaeology.md"

FILE_CITE = re.compile(
    r"^(?P<pre>zip:|josh:)?"
    r"(?P<path>[A-Za-z0-9_./-]+\.(?:py|ipynb|yaml|yml|md|sh))"
    r"(?::(?P<a>\d+)(?:-(?P<b>\d+))?)?$"
)
DIR_CITE = re.compile(
    r"^(?P<pre>zip:|josh:)?"
    r"(?P<path>(?:src|speciesOT|cellot|specs|atlas-paper-vae|scripts|docs)"
    r"/[A-Za-z0-9_./-]*/?)$"
)
ROOT_CITE = re.compile(
    r"^(?P<path>pyproject\.toml|example_debugging\.py)"
    r"(?::(?P<a>\d+)(?:-(?P<b>\d+))?)?$"
)


def find_josh():
    env = os.environ.get("SPECIESOT_JOSH")
    candidates = []
    if env:
        candidates.append(Path(env))
    candidates.append(REPO.parent / "joshuaprice-speciesot")
    for path in candidates:
        if (path / "notebook_descriptions.md").is_file():
            return path
    return None


def find_zip():
    env = os.environ.get("SPECIESOT_SRC_ZIP")
    candidates = []
    if env:
        candidates.append(Path(env))
    candidates.append(
        Path("/home/ubuntu/.cursor/projects/agent-repos-joshuaprice-speciesot/uploads/src_aa1d.zip")
    )
    for path in candidates:
        if path.is_file():
            return path
    return None


def line_count(text):
    # Match wc -l when the file ends in a newline, and still count a last
    # partial line when it does not.
    if text == "":
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def parse(token):
    for pattern, kind in ((FILE_CITE, "file"), (ROOT_CITE, "file"), (DIR_CITE, "dir")):
        match = pattern.fullmatch(token)
        if not match:
            continue
        pre = match.groupdict().get("pre") or ""
        start = match.groupdict().get("a")
        end = match.groupdict().get("b") or start
        return {
            "kind": kind,
            "root": pre[:-1] if pre else "repo",
            "path": match.group("path").rstrip("/"),
            "start": int(start) if start else None,
            "end": int(end) if end else None,
        }
    return None


def resolve_text(item, josh, zf):
    path = item["path"]
    root = item["root"]
    if root == "repo":
        full = REPO / path
        if item["kind"] == "file" and not full.is_file() and "/" not in path:
            hits = [p for p in REPO.rglob(path) if ".ipynb_checkpoints" not in str(p)]
            if len(hits) == 1:
                full = hits[0]
        if item["kind"] == "dir":
            return full, None
        if not full.is_file():
            return full, None
        return full, full.read_text(errors="replace")
    if root == "josh":
        if josh is None:
            return None, None
        full = josh / path
        if item["kind"] == "dir":
            return full, None
        if not full.is_file():
            return full, None
        return full, full.read_text(errors="replace")
    if zf is None or path not in zf.namelist():
        return None, None
    return path, zf.read(path).decode("utf-8", errors="replace")


def check_item(item, josh, zf, errors):
    full, text = resolve_text(item, josh, zf)
    label = f"{item['root']}:{item['path']}"
    if item["kind"] == "dir":
        if item["root"] == "zip":
            errors.append(f"{label} directory citations are not used for the zip")
            return
        if full is None or not full.is_dir():
            errors.append(f"missing directory {label}")
        return
    if text is None:
        if item["root"] == "josh" and josh is None:
            errors.append(f"josh checkout not found for {label}")
        elif item["root"] == "zip" and zf is None:
            errors.append(f"upload zip not found for {label}")
        else:
            errors.append(f"missing file {label}")
        return
    if item["start"] is None:
        return
    count = line_count(text)
    if item["start"] < 1 or item["end"] < item["start"] or item["end"] > count:
        errors.append(
            f"line range {item['start']}-{item['end']} outside {label} ({count} lines)"
        )


def notebooks():
    found = []
    for path in REPO.rglob("*.ipynb"):
        if ".ipynb_checkpoints" in path.parts:
            continue
        found.append(path.relative_to(REPO).as_posix())
    return sorted(found)


def main():
    errors = []
    if not REPORT.is_file():
        errors.append(f"missing report {REPORT}")
    md_files = sorted(LEARNING.rglob("*.md"))
    josh = find_josh()
    zip_path = find_zip()
    zf = zipfile.ZipFile(zip_path) if zip_path else None
    seen = 0
    for md in md_files:
        text = md.read_text(errors="replace")
        for token in re.findall(r"`([^`]+)`", text):
            item = parse(token)
            if item is None:
                continue
            seen += 1
            check_item(item, josh, zf, errors)
    report = REPORT.read_text(errors="replace") if REPORT.is_file() else ""
    for rel in notebooks():
        if f"`{rel}`" not in report:
            errors.append(f"notebook missing from report: {rel}")
    if zf is not None:
        zf.close()
    print(f"checked {seen} citations in {len(md_files)} markdown files")
    print(f"notebooks required in the report: {len(notebooks())}")
    if errors:
        print(f"{len(errors)} failures")
        for err in errors:
            print(err)
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
