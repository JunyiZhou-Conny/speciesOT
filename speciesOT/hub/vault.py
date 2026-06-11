"""Render ModelRecord instances as Obsidian-ready vault notes.

This is the *graph* counterpart to `render.py`'s human model cards.

Difference from `render.py` (and why this is a separate artifact):
- Output goes to `docs/experiments/` (TRACKED by git → syncs to the Mac), not
  `docs/model_cards/` (gitignored, HPC-only, carries absolute figure paths that
  break on the Mac).
- Each note carries YAML **frontmatter** (Obsidian Properties / Dataview),
  **tags** (graph color-groups + filters), and **`[[wikilinks]]`** to its scGen
  sibling and to the concept notes it exemplifies. Those links are what make
  Obsidian's graph view self-assemble — see `docs/obsidian_setup.md`.
- No absolute-path image embeds (they'd be broken links on the Mac). The note
  instead points back to the on-HPC rich card + model dir as plain paths.

The vault command (`./hub vault`) writes one note per model plus an index.
Concept notes linked here may not all exist yet; Obsidian renders missing
targets as "unresolved" placeholder nodes, which doubles as a to-write list.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from speciesOT.hub.catalog import EvalRecord, ModelRecord

# Vault lives in docs/ (the folder the user opens as an Obsidian vault).
DOCS_DIR = Path("/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/docs")
DEFAULT_EXPERIMENTS_DIR = DOCS_DIR / "experiments"

# Display labels per family (mirrors render.py).
_FAMILY_LABEL = {
    "scgen": "scGen",
    "impact_cellot": "IMPACT_CellOT",
    "cellot_celltype": "CellOT (cell-type framing, abandoned)",
    "cellot_legacy": "CellOT (legacy crossspecies)",
    "cellot_unresolved": "CellOT (unresolved — needs review)",
    "unknown": "unknown",
}

# Wikilink target (note basename, no extension) for each family's concept note.
_FAMILY_CONCEPT = {
    "scgen": "scGen",
    "impact_cellot": "IMPACT_CellOT",
    "cellot_celltype": "CellOT cell-type framing",
    "cellot_legacy": "CellOT legacy crossspecies",
}


def run_id_to_basename(run_id: str) -> str:
    """'gpu/hvg_..._m2_ood/impact_cellot' -> 'gpu__hvg_..._m2_ood__impact_cellot'.

    Matches render.py's flat-filename scheme (minus the .md) so wikilinks and
    filenames agree.
    """
    return run_id.replace("/", "__")


# --------------------------------------------------------------------------- #
# YAML frontmatter (a tiny, predictable emitter — Obsidian Properties are picky
# about exotic YAML styles, so we double-quote every string scalar).
# --------------------------------------------------------------------------- #

def _yaml_str(s) -> str:
    s = str(s).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def _yaml_scalar(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return f"{v:.6g}"
    return _yaml_str(v)


def _frontmatter_block(props: "dict[str, object]") -> str:
    """Render an ordered dict as a YAML frontmatter block. None/empty skipped."""
    lines = ["---"]
    for key, val in props.items():
        if val is None:
            continue
        if isinstance(val, list):
            if not val:
                continue
            lines.append(f"{key}:")
            for item in val:
                lines.append(f"  - {_yaml_scalar(item)}")
        else:
            lines.append(f"{key}: {_yaml_scalar(val)}")
    lines.append("---")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Derivations
# --------------------------------------------------------------------------- #

def _mode(rec: ModelRecord) -> Optional[str]:
    if rec.train_includes_holdout is True:
        return "iid"
    if rec.train_includes_holdout is False:
        return "ood"
    return None


def _data_version(rec: ModelRecord) -> Optional[str]:
    """Extract a 'v07'/'v08' tag from the data_file or run_id, if present."""
    hay = f"{rec.data_file or ''} {rec.run_id}"
    m = re.search(r"_v(\d{2,})", hay)
    return f"v{m.group(1)}" if m else None


def _headline_eval(rec: ModelRecord) -> Optional[EvalRecord]:
    """Prefer the data-space eval (biologically interpretable), else first."""
    if not rec.evals:
        return None
    ds = [e for e in rec.evals if e.space == "data_space"]
    return (ds + rec.evals)[0]


def _tags_for(rec: ModelRecord) -> "list[str]":
    tags: list[str] = [rec.family]
    if rec.hvg_method:
        tags.append(f"hvg/{rec.hvg_method}")
    mode = _mode(rec)
    if mode:
        tags.append(f"mode/{mode}")
    if rec.framing:
        tags.append(f"framing/{rec.framing}")
    ver = _data_version(rec)
    if ver:
        tags.append(f"data/{ver}")
    return tags


def _concept_links_for(rec: ModelRecord) -> "list[str]":
    """Wikilink basenames for the concept notes this run exemplifies."""
    links: list[str] = []
    fam_concept = _FAMILY_CONCEPT.get(rec.family)
    if fam_concept:
        links.append(fam_concept)
    # Atlas preprocessing always involves the enforced assay filter (§5.10).
    links.append("assay filter")
    if _mode(rec) is not None:
        links.append("OOD vs IID evaluation")
    if rec.datasplit_strategy == "toggle_ood":
        links.append("OOD split stratification")
    ev = _headline_eval(rec)
    has_extended = ev is not None and (
        ev.frac_gap_closed is not None
        or ev.headline_mmd_floor is not None
        or ev.headline_mmd_ceiling is not None
    )
    if has_extended:
        links += ["MMD floor and ceiling", "frac_gap_closed"]
    # IMPACT decodes through the AE → the round-trip tax concept applies.
    if rec.family == "impact_cellot" and ev is not None and ev.space == "data_space":
        links.append("AE round-trip tax")
    # De-dup while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for x in links:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _sibling_run_ids(rec: ModelRecord, all_ids: "set[str]") -> "list[str]":
    """The scGen<->IMPACT sibling in the same experiment dir, if catalogued."""
    parts = rec.run_id.rsplit("/", 1)
    if len(parts) != 2:
        return []
    parent, leaf = parts
    candidates = {"impact_cellot", "scgen"} - {leaf}
    out = []
    for c in candidates:
        cand = f"{parent}/{c}"
        if cand in all_ids:
            out.append(cand)
    return out


# --------------------------------------------------------------------------- #
# Note rendering
# --------------------------------------------------------------------------- #

def _fmt_num(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        if v != 0 and abs(v) < 0.01:
            return f"{v:.2e}"
        return f"{v:.4f}"
    return str(v)


def render_experiment_note(rec: ModelRecord, all_ids: "set[str]") -> str:
    ev = _headline_eval(rec)
    mode = _mode(rec)
    ver = _data_version(rec)

    props: dict[str, object] = {
        "experiment_id": run_id_to_basename(rec.run_id),
        "run_id": rec.run_id,
        "family": rec.family,
        "status": rec.status,
        "hvg_method": rec.hvg_method,
        "framing": rec.framing,
        "source": rec.source,
        "target": rec.target,
        "holdout": rec.holdout_cell_types or None,
        "mode": mode,
        "data_version": ver,
        "data_file": rec.data_file,
    }
    if ev is not None:
        props["eval_space"] = ev.space
        props["r2"] = ev.headline_r2_means
        props["mmd"] = ev.headline_mmd
        # North-star (AE-honest) metrics first — these are what the MOC sorts on.
        props["frac_gap_closed_decoded"] = ev.frac_gap_closed_decoded
        props["frac_r2_closed_decoded"] = ev.frac_r2_closed_decoded
        props["mean_js"] = ev.headline_js
        # Raw-frame (secondary; unreliable for IMPACT — see §5.9).
        props["mmd_floor"] = ev.headline_mmd_floor
        props["mmd_ceiling"] = ev.headline_mmd_ceiling
        props["frac_gap_closed_raw"] = ev.frac_gap_closed
    props["tags"] = _tags_for(rec)

    parts: list[str] = [_frontmatter_block(props), ""]
    parts.append(f"# {rec.run_id}")
    parts.append("")
    parts.append(
        f"**{_FAMILY_LABEL.get(rec.family, rec.family)}** · status `{rec.status}`"
        + (f" · holdout `{', '.join(rec.holdout_cell_types)}`" if rec.holdout_cell_types else "")
        + (f" · mode `{mode}`" if mode else "")
    )
    parts.append("")

    # Sibling (the strongest experiment-to-experiment edge: IMPACT <-> scGen).
    sibs = _sibling_run_ids(rec, all_ids)
    if sibs:
        sib_links = " · ".join(f"[[{run_id_to_basename(s)}]]" for s in sibs)
        parts.append(f"**Sibling in this experiment:** {sib_links}")
        parts.append("")

    # Concepts (experiment -> concept edges).
    concepts = _concept_links_for(rec)
    if concepts:
        parts.append("**Concepts this run touches:** " + " · ".join(f"[[{c}]]" for c in concepts))
        parts.append("")

    # Compact metrics table (the headline eval).
    if ev is not None:
        parts.append(f"## Headline metrics — `{ev.eval_id}`")
        parts.append("")
        parts.append("| Metric | Value |")
        parts.append("|---|---|")
        parts.append(f"| R² (means, squared) | {_fmt_num(ev.headline_r2_means)} |")
        parts.append(f"| MMD | {_fmt_num(ev.headline_mmd)} |")
        if ev.frac_gap_closed_decoded is not None or ev.frac_r2_closed_decoded is not None:
            parts.append(f"| **frac_gap_closed (decoded, north-star)** | {_fmt_num(ev.frac_gap_closed_decoded)} |")
            parts.append(f"| frac_r2_closed (decoded) | {_fmt_num(ev.frac_r2_closed_decoded)} |")
        if ev.headline_mmd_floor is not None or ev.headline_mmd_ceiling is not None:
            parts.append(f"| MMD floor / ceiling (raw) | {_fmt_num(ev.headline_mmd_floor)} / {_fmt_num(ev.headline_mmd_ceiling)} |")
            parts.append(f"| frac_gap_closed (raw, unreliable) | {_fmt_num(ev.frac_gap_closed)} |")
        if ev.headline_js is not None:
            parts.append(f"| mean per-gene JS (KL-style) | {_fmt_num(ev.headline_js)} |")
        parts.append(f"| n_cells present | {', '.join(map(str, ev.n_cells_present)) or '—'} |")
        parts.append("")
        if len(rec.evals) > 1:
            others = ", ".join(f"`{e.eval_id}`" for e in rec.evals if e is not ev)
            parts.append(f"_Other evals on disk: {others}._")
            parts.append("")
    else:
        parts.append("_No evaluations on disk yet._")
        parts.append("")

    # Provenance + a pointer back to the rich HPC-only card (figures live there).
    parts.append("## On-disk references (HPC)")
    parts.append("")
    parts.append(f"- Model dir: `{rec.model_dir}`")
    parts.append(f"- Rich card (figures, HPC-only): `docs/model_cards/{run_id_to_basename(rec.run_id)}.md`")
    parts.append(f"- Regenerate this note: `./hub vault`")
    parts.append("")

    parts.append("---")
    parts.append("See also: [[Hub Experiments MOC]] · [[conceptual_framework]]")
    parts.append("")
    return "\n".join(parts)


def write_experiment_note(rec: ModelRecord, all_ids: "set[str]", out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_id_to_basename(rec.run_id)}.md"
    out_path.write_text(render_experiment_note(rec, all_ids))
    return out_path


def write_experiments_index(records: "list[ModelRecord]", out_dir: Path) -> Path:
    """A plain index note for the experiments/ folder (works without Dataview)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "_experiments_index.md"

    by_family: dict[str, list[ModelRecord]] = {}
    for r in sorted(records, key=lambda r: r.run_id):
        by_family.setdefault(r.family, []).append(r)
    family_order = ["impact_cellot", "scgen", "cellot_celltype", "cellot_legacy", "cellot_unresolved", "unknown"]

    lines = [
        _frontmatter_block({"title": "Experiments index", "tags": ["moc"]}),
        "",
        "# Experiments index",
        "",
        f"Auto-generated by `./hub vault` ({len(records)} models). "
        "For a live filterable table install Dataview and see [[Hub Experiments MOC]].",
        "",
    ]
    for fam in family_order:
        if fam not in by_family:
            continue
        members = by_family[fam]
        lines.append(f"## {_FAMILY_LABEL.get(fam, fam)} ({len(members)})")
        lines.append("")
        for r in members:
            base = run_id_to_basename(r.run_id)
            ev = _headline_eval(r)
            bit = ""
            if ev is not None and ev.headline_r2_means is not None:
                bit = f" — R²={ev.headline_r2_means:.3f}"
                if ev.headline_mmd is not None:
                    bit += f", MMD={ev.headline_mmd:.3f}"
            lines.append(f"- [[{base}]]{bit}")
        lines.append("")

    out_path.write_text("\n".join(lines))
    return out_path
