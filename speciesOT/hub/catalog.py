"""Dataclasses for the hub's model catalog.

Per the hub-design resolution log (REFACTOR_WALKTHROUGH_2026-05-24.md):
- `project_phase` is NOT a single string; it's replaced by orthogonal
  structured fields (data_source, normalization, hvg_method, etc.).
- 4 model families: scgen / impact_cellot / cellot_celltype / cellot_legacy.
- One EvalRecord per `evals_*/` subdir (not per ncells row).
- (Z) hybrid: full evals.csv schema preserved in `metrics_full`, headline
  summary fields extracted for fast filtering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd


@dataclass
class EvalRecord:
    """One record per `evals_*/` subdirectory of a model dir.

    Compound key: (parent ModelRecord.run_id, eval_id) where eval_id is
    the subdir name (e.g. "evals_ood_data_space").
    """

    eval_id: str
    space: Optional[str]
    setting: Optional[str]
    eval_dir: Path
    evals_csv_path: Path
    imputed_h5ad_path: Optional[Path]
    metrics_full: pd.DataFrame
    headline_r2_means: Optional[float]
    headline_mmd: Optional[float]
    n_cells_present: list[int]
    last_run_at: Optional[datetime]


@dataclass
class ModelRecord:
    """One record per trained model directory."""

    # Identity
    run_id: str
    model_dir: Path

    # Family (4 values: scgen / impact_cellot / cellot_celltype / cellot_legacy)
    family: str
    family_alias_seen: str

    # Preprocessing
    data_source: Optional[str]
    data_file: Optional[str]
    normalization: Optional[str]
    log1p_applied: Optional[bool]
    hvg_method: Optional[str]
    hvg_input_layer: Optional[str]
    hvg_batch_key: Optional[str]

    # Framing
    framing: Optional[str]
    condition: Optional[str]
    source: Optional[str]
    target: Optional[str]
    transport_direction: Optional[str]

    # Holdout
    holdout_cell_types: Optional[list[str]]
    holdout_species: Optional[str]
    train_includes_holdout: Optional[bool]
    datasplit_strategy: Optional[str]

    # Architecture
    model_name: Optional[str]
    hidden_units: Optional[list[int]]
    latent_dim: Optional[int]
    n_iters: Optional[int]
    n_inner_iters: Optional[int]
    batch_size: Optional[int]
    lr: Optional[float]
    optimizer: Optional[str]

    # AE pointer
    ae_emb_path: Optional[str]

    # Lineage / provenance
    generated_by: Optional[str]
    created_at: Optional[datetime]
    last_modified: Optional[datetime]

    # Status
    status: str

    # Evaluations
    evals: list[EvalRecord] = field(default_factory=list)

    # Free-form (for hand-curated notes ported from build_experiments_inventory)
    notes: str = ""


@dataclass
class Catalog:
    """Container of ModelRecord instances with a few convenience helpers."""

    records: list[ModelRecord]
    walk_roots: list[Path]
    discovered_at: datetime

    def by_run_id(self, run_id: str) -> Optional[ModelRecord]:
        for r in self.records:
            if r.run_id == run_id:
                return r
        return None

    def filter(self, **kw) -> "Catalog":
        """Simple equality filter on top-level ModelRecord fields."""
        out = []
        for r in self.records:
            ok = True
            for k, v in kw.items():
                actual = getattr(r, k, None)
                # Allow filtering on holdout_human-readable shorthand: match against any item in the list.
                if isinstance(actual, list):
                    if v not in actual:
                        ok = False
                        break
                elif actual != v:
                    ok = False
                    break
            if ok:
                out.append(r)
        return Catalog(records=out, walk_roots=self.walk_roots, discovered_at=self.discovered_at)

    def __len__(self) -> int:
        return len(self.records)

    def __iter__(self):
        return iter(self.records)
