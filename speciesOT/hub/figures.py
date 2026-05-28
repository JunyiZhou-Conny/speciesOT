"""Figure attachment + matcher for hub model cards (v0.5).

Two responsibilities:
1. `list_attached_figures(model_dir)` — given a model dir, return every
   image file under `<model_dir>/figures/`. Used by `render.py` to inline
   figures in markdown cards.
2. `match_baseline_outputs_to_models(catalog)` — scan figures under
   `speciesOT/baseline/analysis/*_outputs/`, try to match each one to one
   or more ModelRecord instances via filename-pattern heuristics, and
   create symlinks at `<model_dir>/figures/<figname>` so the cards pick
   them up.

The matcher is intentionally conservative: only per-experiment-cell figures
attach (e.g. figure_f_cd8_pearson_residuals_dataspace_ncells80.png).
Matrix-wide figures (method_gap_*, marker_rank_heatmap, figure_F_R2_OOD,
paper figure replicas) are NOT attached to individual model cards — they
belong to a separate matrix-summary view (planned for a later milestone).

Use `./hub attach-figures --dry-run` to preview the matches without
creating any symlinks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

from speciesOT.hub.catalog import Catalog, ModelRecord
from speciesOT.hub.discover import WORKSPACE_ROOT


BASELINE_OUTPUTS = WORKSPACE_ROOT / "speciesOT" / "baseline" / "analysis"

_IMG_SUFFIXES = {".png", ".pdf", ".svg", ".jpg", ".jpeg"}

# Known HVG method tokens (longest-prefix first when checking).
_HVG_TOKENS = [
    "pearson_residuals",
    "seurat_v3_paper",
    "seurat_v3",
    "cell_ranger",
    "seurat",
]

# Short-form aliases that appear in some figure filenames (e.g. `umap_atlas_ref_cd8_pearson_scgen_impact.png`).
# Only used in figure-fingerprint extraction; canonical HVG values still come from _HVG_TOKENS.
_HVG_FILENAME_ALIASES: dict[str, str] = {
    "pearson": "pearson_residuals",
}

# Map matrix group letters (used in run_ids) to the filename-friendly group
# names (used in figure filenames). e.g. `hvg_seurat_d_ood` -> "cd4".
# Per scripts/regenerate_hvg_flavor_run_matrix.py:
#   a = cd8 only
#   b = cd8 + thymocyte
#   c = all T-cell subtypes (cd4+cd8+thymo)
#   d = cd4 only
#   m2 = monocyte holdout
_GROUP_LETTER_TO_NAME: dict[str, str] = {
    "a": "cd8",
    "b": "cd8_thymo",
    "c": "tcell_subtypes",
    "d": "cd4",
    "m1": "m1",
    "m2": "m2",
    "m3": "m3",
    "m4": "m4",
    "t1": "t1",
    "t2": "t2",
    "t3": "t3",
    "t4": "t4",
}


# ---------------------------------------------------------------------------
# Reading attached figures from a model card's figures/ subdir
# ---------------------------------------------------------------------------

def attached_figures_dir(model_dir: Path) -> Path:
    return model_dir / "figures"


def list_attached_figures(model_dir: Path) -> list[Path]:
    """Return all image files under `<model_dir>/figures/` (incl. symlinks)."""
    figures_dir = attached_figures_dir(model_dir)
    if not figures_dir.exists():
        return []
    out: list[Path] = []
    for p in sorted(figures_dir.iterdir()):
        if p.is_file() and p.suffix.lower() in _IMG_SUFFIXES:
            out.append(p)
    return out


# ---------------------------------------------------------------------------
# Matcher
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModelFingerprint:
    """The (group, hvg, mode) tuple describing what a model is, for matching."""
    group: Optional[str]   # filename-friendly: cd8, cd4, m2, etc.
    hvg: Optional[str]     # pearson_residuals, seurat_v3, ...
    mode: Optional[str]    # ood, iid


def _model_fingerprint(rec: ModelRecord) -> Optional[ModelFingerprint]:
    """Extract a (group, hvg, mode) fingerprint from a model record.

    Returns None for models that don't fit the standard matrix shape
    (the user's atlas_full, legacy_crossspecies, etc. won't auto-match).
    """
    parts = rec.run_id.split("/")
    if len(parts) < 2:
        return None
    tag = parts[-2]  # parent experiment dir name (e.g. hvg_seurat_d_ood)
    if not tag.startswith("hvg_"):
        return None  # only the modern matrix produces auto-matchable figures

    # Tag structure: hvg_<flavor>_<group_letter>_<mode>[_<suffix>]
    # We've already extracted hvg_method from data_file in discover.py, so use that.
    hvg = rec.hvg_method
    # Extract group + mode from the tag tail.
    # Strip "hvg_<flavor>_" prefix.
    rest = tag[len("hvg_"):]
    # Strip flavor prefix (longest first).
    for f in _HVG_TOKENS:
        if rest.startswith(f + "_"):
            rest = rest[len(f) + 1:]
            break
    # rest is now like "d_ood" or "m2_ood_uncapped".
    sub = rest.split("_")
    group_letter = sub[0] if sub else None
    mode = sub[1] if len(sub) > 1 and sub[1] in {"ood", "iid"} else None
    group_name = _GROUP_LETTER_TO_NAME.get(group_letter) if group_letter else None
    return ModelFingerprint(group=group_name, hvg=hvg, mode=mode)


# Mode regex: `ood` or `iid` bounded by non-letter on both sides (so it
# doesn't fire inside e.g. "ribosome_oxidation"). Allow `.` (extension dot)
# as a trailing boundary so we catch `..._ood.pdf` too.
_MODE_RE = re.compile(r"(?:^|[_\-])(ood|iid)(?:[_\-.]|$)")

# Only scan these output dirs by default. They're the ones producing per-cell
# figures (one figure per experiment-cell, possibly showing both scgen+impact_cellot).
# Other dirs (bcg_*, paper_figure_replica_outputs, figure_g_outputs, atlas_full_outputs,
# hvg_flavor_outputs, hvg_flavor_results_outputs, immune_ontology_outputs, uncapped_outputs)
# produce matrix-wide or domain-specific figures that don't cleanly attach to a single
# model — those will be handled by a separate matrix-view milestone.
_PER_CELL_OUTPUT_DIRS: list[str] = [
    "presentation_figure_outputs",
    "hvg_flavor_nb14_outputs/figures",
    "umap_learn_outputs",
]


def _figure_fingerprint(figure_name: str) -> Optional[ModelFingerprint]:
    """Extract a fingerprint from a figure filename.

    Returns None if no recognizable pattern.
    """
    name = figure_name.lower()
    # HVG method (longest canonical first; then check filename-only aliases)
    hvg = None
    for h in _HVG_TOKENS:
        if h in name:
            hvg = h
            break
    if hvg is None:
        for alias, canonical in _HVG_FILENAME_ALIASES.items():
            # word-boundary match so "pearson" doesn't fire on accidental substring
            if re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", name):
                hvg = canonical
                break
    # Group: scan for known group names (longest first)
    group = None
    for gname in ["cd8_thymo", "tcell_subtypes", "cd8", "cd4", "m1", "m2", "m3", "m4", "t1", "t2", "t3", "t4"]:
        if re.search(rf"(?<![a-z]){re.escape(gname)}(?![a-z])", name):
            group = gname
            break
    # Mode (explicit)
    mode_m = _MODE_RE.search(name)
    mode = mode_m.group(1) if mode_m else None
    if not group and not hvg:
        return None  # nothing actionable
    return ModelFingerprint(group=group, hvg=hvg, mode=mode)


def _is_compatible(fig_fp: ModelFingerprint, mod_fp: ModelFingerprint) -> bool:
    """Decide whether the figure should be attached to the model."""
    # Group required to match if both sides have one.
    if fig_fp.group and mod_fp.group and fig_fp.group != mod_fp.group:
        return False
    # HVG method required to match if both sides have one.
    if fig_fp.hvg and mod_fp.hvg and fig_fp.hvg != mod_fp.hvg:
        return False
    # Mode: if figure specifies a mode, require model to match.
    # If figure has no explicit mode, accept any model mode.
    if fig_fp.mode and mod_fp.mode and fig_fp.mode != mod_fp.mode:
        return False
    # At least one of (group, hvg) must be present on the figure (else any match would be too permissive).
    if not (fig_fp.group or fig_fp.hvg):
        return False
    # And at least one must actually overlap.
    if not (
        (fig_fp.group and mod_fp.group and fig_fp.group == mod_fp.group)
        or (fig_fp.hvg and mod_fp.hvg and fig_fp.hvg == mod_fp.hvg)
    ):
        return False
    return True


def iter_baseline_figures() -> Iterator[Path]:
    """Yield every image file under the curated set of per-cell output dirs.

    See _PER_CELL_OUTPUT_DIRS for the included paths. Other dirs (bcg_*,
    paper_figure_replica_outputs, etc.) are skipped because they produce
    matrix-wide or domain-specific figures that don't cleanly attach to
    one model.
    """
    if not BASELINE_OUTPUTS.exists():
        return
    for rel in _PER_CELL_OUTPUT_DIRS:
        d = BASELINE_OUTPUTS / rel
        if not d.exists() or not d.is_dir():
            continue
        for p in d.rglob("*"):
            if p.is_file() and p.suffix.lower() in _IMG_SUFFIXES:
                yield p


@dataclass
class FigureMatch:
    source: Path
    target_model_dir: Path
    target_link: Path
    fig_fp: ModelFingerprint
    mod_fp: ModelFingerprint


def match_all(catalog: Catalog) -> list[FigureMatch]:
    """For each figure under baseline/*_outputs/, find matching models.

    Returns a list of FigureMatch objects describing what would be linked.
    """
    matches: list[FigureMatch] = []
    # Precompute model fingerprints.
    model_fps: list[tuple[ModelRecord, ModelFingerprint]] = []
    for rec in catalog.records:
        mfp = _model_fingerprint(rec)
        if mfp is None:
            continue
        model_fps.append((rec, mfp))

    for fig_path in iter_baseline_figures():
        ffp = _figure_fingerprint(fig_path.name)
        if ffp is None:
            continue
        for rec, mfp in model_fps:
            if _is_compatible(ffp, mfp):
                target_dir = attached_figures_dir(rec.model_dir)
                target_link = target_dir / fig_path.name
                matches.append(
                    FigureMatch(
                        source=fig_path,
                        target_model_dir=rec.model_dir,
                        target_link=target_link,
                        fig_fp=ffp,
                        mod_fp=mfp,
                    )
                )
    return matches


def apply_matches(matches: list[FigureMatch], overwrite: bool = False) -> dict[str, int]:
    """Create the symlinks. Returns stats dict."""
    stats = {"created": 0, "skipped_existing": 0, "errors": 0}
    seen_targets: set[Path] = set()
    for m in matches:
        if m.target_link in seen_targets:
            continue
        seen_targets.add(m.target_link)
        try:
            m.target_link.parent.mkdir(parents=True, exist_ok=True)
            if m.target_link.exists() or m.target_link.is_symlink():
                if not overwrite:
                    stats["skipped_existing"] += 1
                    continue
                m.target_link.unlink()
            # Use absolute path for the symlink target so it works regardless of cwd.
            m.target_link.symlink_to(m.source.resolve())
            stats["created"] += 1
        except OSError:
            stats["errors"] += 1
    return stats


def summarize_matches(matches: list[FigureMatch]) -> str:
    """Render a human-readable summary of pending matches."""
    if not matches:
        return "(no matches found)"
    # Group by target model dir
    by_target: dict[Path, list[FigureMatch]] = {}
    for m in matches:
        by_target.setdefault(m.target_model_dir, []).append(m)
    lines: list[str] = []
    n_models = len(by_target)
    n_figures = len({m.source for m in matches})
    lines.append(f"{len(matches)} (figure, model) pairs across {n_models} models from {n_figures} unique figures.")
    lines.append("")
    for model_dir, ms in sorted(by_target.items()):
        rel = model_dir.relative_to(WORKSPACE_ROOT)
        lines.append(f"{rel}")
        for m in ms:
            src_rel = m.source.relative_to(BASELINE_OUTPUTS) if m.source.is_relative_to(BASELINE_OUTPUTS) else m.source
            lines.append(f"  ← {src_rel}")
        lines.append("")
    return "\n".join(lines)
