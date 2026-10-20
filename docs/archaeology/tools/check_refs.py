"""Check that every citation in docs/archaeology/ points at something real.

A citation is a backticked span such as `conny:path`, `conny:path#c12`,
`conny:path:40-52`, `conny@sha`, `josh@main:path`, `fasrc:BK/path` or
`mac:path` (prefixes are defined in sources.md). Bare tokens without spaces are
checked too.

For each one the script checks that:

- the file exists in the right repository and ref,
- the commit exists,
- a notebook cell index or line range is in range.

FASRC paths are looked up in a local mirror first. Paths missing from the
mirror can be checked in one batched `ssh fasrc` call with --remote.

Read-only. Prints a summary and every citation that did not resolve; exits 1
if any failed.

    python docs/archaeology/tools/check_refs.py \
        --josh $SRC/speciesOT-josh --autoresearch $SRC/scgen-cellot-autoresearch \
        --ablation $SRC/scgen-cellot-ablation --ai-package $SRC/speciesost-package \
        --fasrc-mirror $SRC/fasrc --remote
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

BK = "/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT-backup-2026-10-01/speciesOT"
PREFIX = r"(?:conny|josh|autoresearch|ablation|ai_package|fasrc|mac)"
BACKTICK = re.compile(r"`([^`\n]+)`")
BARE = re.compile(rf"(?<![\w/`]){PREFIX}[@:][^\s`|)\],;]+")
# path, optional "#c<cell>[-<cell>]" or ":<line>[-<line>][, <line>[-<line>]...]" suffix
LOCATOR = re.compile(
    r"^(?P<path>.+?)(?:#c(?P<cell>\d+)(?:-(?P<cell2>\d+))?"
    r"|:(?P<lines>\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*))?$"
)
SHA = re.compile(r"^[0-9a-f]{7,40}$")


def git_ok(repo: Path, *args: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True).returncode == 0


def git_blob(repo: Path, ref: str, path: str) -> bytes | None:
    out = subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{path}"], capture_output=True)
    return out.stdout if out.returncode == 0 else None


def check_locator(data: bytes, loc: re.Match) -> str | None:
    """Return an error string, or None if the cell or line locator is in range."""
    if loc["cell"] is not None:
        try:
            n_cells = len(json.loads(data).get("cells", []))
        except ValueError:
            return "not a notebook"
        last = int(loc["cell2"] or loc["cell"])
        return None if last < n_cells else f"cell {last} >= {n_cells} cells"
    if loc["lines"] is not None:
        n_lines = data.count(b"\n") + 1
        last = max(int(x) for x in re.findall(r"\d+", loc["lines"]))
        return None if last <= n_lines else f"line {last} > {n_lines} lines"
    return None


def expand_braces(pattern: str) -> list[str]:
    """Expand one level of {a,b} alternatives: x/{a,b}/y -> [x/a/y, x/b/y]."""
    m = re.search(r"\{([^{}]*)\}", pattern)
    if not m:
        return [pattern]
    return [alt for part in m.group(1).split(",")
            for alt in expand_braces(pattern[:m.start()] + part + pattern[m.end():])]


class Checker:
    def __init__(self, args: argparse.Namespace) -> None:
        self.conny = args.conny.resolve()
        self.repos = {
            "josh": args.josh, "autoresearch": args.autoresearch,
            "ablation": args.ablation, "ai_package": args.ai_package,
        }
        self.mirror = args.fasrc_mirror
        self.mac_root = args.mac_root
        self.remote_queue: list[tuple[str, str]] = []

    def check(self, cite: str) -> str | None:
        """Return None if OK, 'remote' if it needs FASRC, else an error."""
        m = re.match(rf"^({PREFIX})([@:])(.*)$", cite)
        if not m:
            return "unparsed"
        prefix, sep, rest = m.groups()
        if prefix == "fasrc":
            return self._fasrc(cite, rest)
        if prefix == "mac":
            loc = LOCATOR.match(rest)
            path = self.mac_root / loc["path"]
            return None if path.exists() else "missing on Mac"
        if prefix == "conny":
            if sep == "@":
                return None if SHA.match(rest) and git_ok(self.conny, "cat-file", "-e", f"{rest}^{{commit}}") else "unknown commit"
            return self._in_repo(self.conny, "HEAD", rest, worktree=True)
        repo = self.repos[prefix]
        if repo is None:
            return "repo not given"
        if sep == "@":
            ref, _, path = rest.partition(":")
            if not path:
                return None if SHA.match(ref) and git_ok(repo, "cat-file", "-e", f"{ref}^{{commit}}") else "unknown commit"
            ref = ref if ref == "HEAD" or SHA.match(ref) else f"origin/{ref}"
            return self._in_repo(repo, ref, path)
        return self._in_repo(repo, "HEAD", rest)

    def _in_repo(self, repo: Path, ref: str, rest: str, worktree: bool = False) -> str | None:
        loc = LOCATOR.match(rest)
        path = loc["path"].rstrip("/")
        if any(ch in path for ch in "*{}?"):
            return None if self._glob_matches(repo, ref, path) else "pattern matches nothing"
        data = git_blob(repo, ref, path)
        if data is None and worktree and (repo / path).is_file():
            data = (repo / path).read_bytes()
        if data is None:
            if git_ok(repo, "cat-file", "-e", f"{ref}:{path}") or (worktree and (repo / path).is_dir()):
                return None  # a directory
            return "missing"
        return check_locator(data, loc)

    def _glob_matches(self, repo: Path, ref: str, pattern: str) -> bool:
        names = subprocess.run(["git", "-C", str(repo), "ls-tree", "-r", "--name-only", ref],
                               capture_output=True, text=True).stdout.splitlines()
        for alt in expand_braces(pattern):
            regex = re.compile("^" + re.escape(alt).replace(r"\*", "[^/]*").replace(r"\?", ".") + "$")
            if not any(regex.match(n) for n in names):
                return False
        return True

    def _fasrc(self, cite: str, rest: str) -> str | None:
        loc = LOCATOR.match(rest)
        path = loc["path"].rstrip("/")
        pending = []
        for alt in expand_braces(path):
            absolute = alt.replace("BK/", BK + "/", 1) if alt.startswith("BK/") else alt
            if self.mirror is not None and alt.startswith("BK/"):
                if any(c in alt for c in "*?"):
                    if any(self.mirror.glob(alt)):
                        continue
                else:
                    local = self.mirror / alt
                    if local.is_file():
                        err = check_locator(local.read_bytes(), loc)
                        if err:
                            return err
                        continue
                    if local.is_dir():
                        continue
            pending.append(absolute)
        if not pending:
            return None
        self.remote_queue.extend((cite, p) for p in pending)
        return "remote"

    def run_remote(self) -> dict[str, bool]:
        if not self.remote_queue:
            return {}
        # One ssh call: print the index of every path that exists.
        script = "\n".join(
            f"compgen -G {json.dumps(p)} >/dev/null 2>&1 && echo {i}" if any(c in p for c in "*?")
            else f"test -e {json.dumps(p)} && echo {i}"
            for i, (_, p) in enumerate(self.remote_queue)
        )
        out = subprocess.run(["ssh", "-o", "BatchMode=yes", "fasrc", "bash -s"],
                             input=script, capture_output=True, text=True)
        found = {int(x) for x in out.stdout.split()}
        ok: dict[str, bool] = {}
        for i, (cite, _) in enumerate(self.remote_queue):
            ok[cite] = ok.get(cite, True) and i in found
        return ok


def citations(text: str) -> list[str]:
    spans = [s.strip() for s in BACKTICK.findall(text)]
    cites = [s for s in spans if re.match(rf"^{PREFIX}[@:]", s)]
    stripped = BACKTICK.sub("", text)
    cites += [c.rstrip(".") for c in BARE.findall(stripped)]
    # Skip placeholders such as `conny:<path>` and bare prefixes such as `ablation:`.
    return [c for c in cites if "<" not in c and not re.match(rf"^{PREFIX}(@\w+)?:$", c)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    here = Path(__file__).resolve().parents[3]
    parser.add_argument("--conny", type=Path, default=here)
    parser.add_argument("--docs", type=Path, default=here / "docs" / "archaeology")
    parser.add_argument("--josh", type=Path)
    parser.add_argument("--autoresearch", type=Path)
    parser.add_argument("--ablation", type=Path)
    parser.add_argument("--ai-package", type=Path)
    parser.add_argument("--fasrc-mirror", type=Path)
    parser.add_argument("--mac-root", type=Path, default=Path.home() / "Desktop")
    parser.add_argument("--remote", action="store_true", help="check unmirrored FASRC paths over ssh")
    args = parser.parse_args()

    checker = Checker(args)
    results: dict[str, str | None] = {}
    where: dict[str, set[str]] = {}
    for md in sorted(args.docs.rglob("*.md")):
        for cite in citations(md.read_text()):
            where.setdefault(cite, set()).add(str(md.relative_to(args.docs)))
            if cite not in results:
                results[cite] = checker.check(cite)
    if args.remote:
        for cite, ok in checker.run_remote().items():
            results[cite] = None if ok else "missing on FASRC"
    else:
        for cite, err in results.items():
            if err == "remote":
                results[cite] = "unchecked (not in mirror; use --remote)"

    by_prefix = Counter(re.match(rf"^({PREFIX})", c).group(1) for c in results)
    failed = {c: e for c, e in results.items() if e is not None}
    print(f"checked {len(results)} distinct citations in {len(list(args.docs.rglob('*.md')))} files")
    print("  " + ", ".join(f"{p}: {n}" for p, n in sorted(by_prefix.items())))
    for cite, err in sorted(failed.items()):
        print(f"FAIL {err:<40} {cite}   ({', '.join(sorted(where[cite]))})")
    print("ok" if not failed else f"{len(failed)} failed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
