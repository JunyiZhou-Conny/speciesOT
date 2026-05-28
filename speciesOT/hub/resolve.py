"""Alias resolution and per-phase context overrides.

Ports the `ALIAS_TABLE` and per-phase cellot disambiguation from
`scripts/build_experiments_inventory.py` (the script this hub eventually retires).

The 4-family scheme is from the hub-design resolution log
(REFACTOR_WALKTHROUGH_2026-05-24.md, Q3a):
  scgen / impact_cellot / cellot_celltype / cellot_legacy
"""

from __future__ import annotations

from typing import Optional


# Direct alias → canonical family map. Source: build_experiments_inventory.py:120-139.
_ALIAS_TO_FAMILY: dict[str, str] = {
    "scgen": "scgen",
    "speciesot_scgen": "scgen",
    "impact": "impact_cellot",
    "impact_cellot": "impact_cellot",
    "impact_or": "impact_cellot",
    "swapped_cellot": "impact_cellot",
    "speciesot_cellot": "impact_cellot",
    "speciesot_cellot_swapped": "cellot_celltype",
    "normal_cellot": "cellot_celltype",
    # Bare "cellot" is context-dependent — handled in resolve_family() below.
}

# Phase-dependent disambiguation for the bare "cellot" subdir name.
# Source: build_experiments_inventory.py:193-198.
_CELLOT_PHASE_OVERRIDES: dict[str, str] = {
    "legacy_crossspecies": "cellot_legacy",
    "speciesot_v1": "cellot_celltype",
    "toggle": "cellot_celltype",
}


def resolve_family(subdir_name: str, parent_tag: str) -> tuple[str, str]:
    """Return (canonical_family, family_alias_seen) for a model subdir.

    `parent_tag` is the experiment dir name (parent of the model dir),
    e.g. "hvg_seurat_d_ood", "toggle_t1_iid", "cross_species_ood".
    """
    # Top-level legacy result dirs that ARE the model (no model subdir).
    # In this layout, model_dir = <root>/<experiment>, so subdir_name carries
    # the experiment name and parent_tag is typically just "results".
    if (
        subdir_name.startswith("cross_species_ood")
        or subdir_name.startswith("race")
        or parent_tag.startswith("cross_species_ood")
        or parent_tag.startswith("race")
    ):
        if "scgen" in subdir_name.lower():
            return "scgen", subdir_name
        return "cellot_legacy", subdir_name

    # Bare "cellot" — phase-dependent.
    if subdir_name == "cellot":
        phase = infer_phase(parent_tag)
        if phase in _CELLOT_PHASE_OVERRIDES:
            return _CELLOT_PHASE_OVERRIDES[phase], subdir_name
        return "cellot_unresolved", subdir_name

    canonical = _ALIAS_TO_FAMILY.get(subdir_name)
    if canonical is not None:
        return canonical, subdir_name

    return "unknown", subdir_name


def infer_phase(experiment_tag: str) -> str:
    """Auto-infer the (now-conceptual, non-stored) project phase from a tag.

    Used internally for cellot-subdir disambiguation and for `generated_by`
    inference. Not stored on ModelRecord — that's by design (per Q3 in the
    resolution log).
    """
    tag = experiment_tag.lower()
    if tag.startswith("hvg_"):
        return "hvg_flavor"
    if tag.startswith("toggle_"):
        return "toggle"
    if tag.startswith("renorm_"):
        return "renorm"
    if tag.startswith("atlas_full_"):
        return "atlas_full"
    if tag.startswith("speciesot_"):
        return "speciesot_v1"
    if tag.startswith("cross_species_") or tag.startswith("race"):
        return "legacy_crossspecies"
    if "bcg" in tag:
        return "bcg"
    return "unknown"


def infer_framing(
    family: str,
    condition: Optional[str],
    datasplit_key: Optional[str],
    source: Optional[str],
    target: Optional[str],
) -> str:
    """Derive the conceptual framing from family + config fields."""
    if family == "cellot_legacy":
        return "legacy"
    if family == "cellot_celltype":
        return "cell_type"
    # scgen and impact_cellot
    if source in {"mouse", "human"} or target in {"mouse", "human"}:
        return "species"
    if source in {"control", "ctrl", "unst", "untreated", "ctl"}:
        return "drug"
    return "unknown"


def infer_generated_by(experiment_tag: str) -> Optional[str]:
    """Best-effort match from tag prefix to the generator script that wrote it."""
    tag = experiment_tag.lower()
    if tag.startswith("hvg_"):
        return "generate_hvg_flavor_configs.py"
    if tag.startswith("toggle_"):
        return "generate_toggle_configs.py (deleted; outputs preserved)"
    if tag.startswith("atlas_full_"):
        return "generate_atlas_full_configs.py"
    return None
