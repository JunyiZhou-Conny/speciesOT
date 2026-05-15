"""Build a comprehensive CSV inventory of every CellOT/IMPACT/scGen training run
that exists under this project.

For each model directory that contains a `config.yaml` (and usually a `cache/`
subdir with `last.pt` / `model.pt` / `status`), this script records:

  - where the run lives on disk (relative to the project root)
  - what model family it is (scGen / IMPACT / CellOT) and what its alias has
    been at different points in the project (impact_or, swapped_cellot,
    speciesot_cellot, normal_cellot, ...)
  - which h5ad file it consumed and which scGen embedding it pulled from
  - the holdout key/value, the cell-type group label, and the toggle mode (iid/ood)
  - hyperparameters (n_iters, batch_size, hidden_units, latent_dim, lr)
  - status (done/running/aborted/never_started) and which evals subdirs exist
  - the corresponding train/eval sbatch script and the analysis notebooks that
    consumed it
  - free-form notes (e.g. "iteration 1 -- transport direction was reversed")

The script is side-effect free besides writing the CSV.

Run:
    python scripts/build_experiments_inventory.py
The output is written to: <project_root>/experiments_inventory.csv
"""

from __future__ import annotations

import csv
import datetime as dt
import os
from pathlib import Path
from typing import Optional

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # the script falls back to a small parser

PROJECT = Path("/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT")
GPU = PROJECT / "cellot" / "cellot_gpu"
LEGACY = PROJECT / "cellot" / "cellot"
OUT_CSV = PROJECT / "experiments_inventory.csv"


def _load_yaml(p: Path) -> dict:
    """Tiny YAML loader for the simple configs we have. Uses PyYAML when present."""
    if yaml is not None:
        with open(p) as f:
            return yaml.safe_load(f) or {}
    out: dict = {}
    stack: list = [(0, out)]
    last_key: Optional[str] = None
    for raw in p.read_text().splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        # Pop stack frames whose indent level we've left.
        while stack and indent < stack[-1][0]:
            stack.pop()
            if not stack:
                stack = [(0, out)]
        parent = stack[-1][1]
        if line.startswith("- "):
            val = line[2:].strip().strip("'\"")
            if last_key is not None:
                if not isinstance(parent.get(last_key), list):
                    parent[last_key] = []
                parent[last_key].append(val)
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip().strip("'\"")
            if v == "":
                parent[k] = {}
                stack.append((indent + 2, parent[k]))
                last_key = k
            elif v == "[]":
                parent[k] = []
                last_key = k
            else:
                parent[k] = v
                last_key = k
    return out


def _maybe_mtime(p: Path) -> str:
    if p.exists():
        return dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    return ""


def _read_status(model_dir: Path) -> str:
    s = model_dir / "cache" / "status"
    if s.exists():
        return s.read_text().strip()
    return "never_started"


def _evals_present(model_dir: Path) -> str:
    have_ds = (model_dir / "evals_ood_data_space" / "evals.csv").exists()
    have_ls = (model_dir / "evals_ood_latent_space" / "evals.csv").exists()
    if have_ds and have_ls:
        return "data+latent"
    if have_ds:
        return "data_space"
    if have_ls:
        return "latent_space"
    return "none"


# ---------------------------------------------------------------------------
# Glossary of model-family aliases used across the project's lifetime.
#
# The directory name underneath an experiment folder is *not* a stable signal
# for what kind of model lives there - the convention changed several times.
# The table below maps (experiment_phase, dir_name) -> canonical info.
# ---------------------------------------------------------------------------
ALIAS_TABLE = {
    # cross_species_ood/ at the top level of cellot/cellot[_gpu]/results is
    # always a CellOT trained on 1000-dim raw HVG ortholog space (no scGen).
    # cross_species_ood_scgen* is the matching scGen autoencoder.
    "scgen": ("scGen", "scgen / speciesot_scgen / autoencoder"),
    "speciesot_scgen": ("scGen", "scgen / speciesot_scgen / autoencoder"),
    "cellot": (
        "CellOT",  # interpreted per-experiment; see notes
        "cellot / speciesot_cellot_swapped / normal_cellot",
    ),
    "impact": ("IMPACT", "impact / impact_or / swapped_cellot / speciesot_cellot"),
    "impact_or": ("IMPACT", "impact / impact_or / swapped_cellot / speciesot_cellot"),
    "speciesot_cellot": ("IMPACT", "impact / impact_or / swapped_cellot / speciesot_cellot"),
    "speciesot_cellot_swapped": (
        "CellOT",
        "cellot / speciesot_cellot_swapped / normal_cellot",
    ),
    "normal_cellot": ("CellOT", "cellot / speciesot_cellot_swapped / normal_cellot"),
    "swapped_cellot": ("IMPACT", "impact / impact_or / swapped_cellot / speciesot_cellot"),
}

# Cell ontology lookup so the human can read the CSV without context-switching
CL = {
    "CL:0000084": "T cell (broad)",
    "CL:0000893": "thymocyte",
    "CL:0000624": "CD4+ alpha-beta T cell",
    "CL:0000625": "CD8+ alpha-beta T cell",
    "CL:0000875": "non-classical monocyte",
    "CL:0000576": "monocyte (generic / unclassified)",
    "CL:0000860": "classical monocyte",
    "CL:0002393": "intermediate monocyte",
}


def cl_human(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(f"{v} ({CL.get(v, '?')})" for v in value)
    if isinstance(value, dict):
        # train_test format: {cell_type_ontology_term_id: ...} or {species: ...}
        parts = []
        for k, v in value.items():
            if isinstance(v, list):
                parts.append(
                    f"{k}=[" + ", ".join(f"{x} ({CL.get(x, '?')})" for x in v) + "]"
                )
            else:
                parts.append(f"{k}={v} ({CL.get(v, '?')})" if k == "cell_type_ontology_term_id" else f"{k}={v}")
        return "; ".join(parts)
    return f"{value} ({CL.get(str(value), '?')})"


def transport_direction(model_family: str, source: str, target: str) -> str:
    return f"{source} -> {target}"


def _parse_record(model_dir: Path, project_phase: str, group_label: str,
                  preprocessing: str, mode: str, sbatch_train: str,
                  sbatch_eval: str, notebooks: str, notes: str,
                  data_format: str) -> dict:
    cfg = _load_yaml(model_dir / "config.yaml") if (model_dir / "config.yaml").exists() else {}
    data = cfg.get("data", {}) or {}
    model = cfg.get("model", {}) or {}
    optim = cfg.get("optim", {}) or {}
    training = cfg.get("training", {}) or {}
    dl = cfg.get("dataloader", {}) or {}
    split = cfg.get("datasplit", {}) or {}

    # interpret the directory name -> canonical model family
    sub = model_dir.name
    fam, alias = ALIAS_TABLE.get(sub, ("UNKNOWN", sub))
    # `cellot` directory has different meanings between phases. Override:
    if sub == "cellot" and project_phase.startswith("legacy_crossspecies"):
        fam, alias = "CellOT", "cellot (raw 1000-dim, no scGen)"
    elif sub == "cellot" and project_phase == "speciesot_v1_iter2_groupA":
        fam, alias = "CellOT", "cellot (CellOT framing: non_cd8 -> cd8, holdout=human)"
    elif sub == "cellot" and project_phase == "toggle":
        fam, alias = "CellOT", "cellot (CellOT framing: non_X -> X, holdout=human)"

    # Special-case top-level (no sub-dir) experiments like cross_species_ood
    if sub.startswith("cross_species_ood") or sub.startswith("race"):
        if "scgen" in sub:
            fam, alias = "scGen", "cross_species_ood scGen autoencoder"
        else:
            fam, alias = "CellOT", "CellOT trained on rat-OOD crossspecies dataset"

    # Build the holdout description
    holdout = split.get("holdout") if isinstance(split, dict) else None
    holdout_key = split.get("key") if isinstance(split, dict) else ""
    if isinstance(holdout, dict) and not holdout_key:
        holdout_key = ",".join(sorted(holdout.keys()))
    holdout_value = ""
    if holdout is not None:
        is_cl_dict = isinstance(holdout, dict)
        is_cl_scalar = isinstance(holdout, str) and holdout.startswith("CL:")
        is_cl_list = isinstance(holdout, list) and holdout and str(holdout[0]).startswith("CL:")
        if is_cl_dict or is_cl_scalar or is_cl_list:
            holdout_value = cl_human(holdout)
        else:
            holdout_value = f"{holdout}"

    rec = {
        "exp_id": "",  # filled in caller
        "train_finished": _maybe_mtime(model_dir / "cache" / "last.pt"),
        "project_phase": project_phase,
        "group_label": group_label,
        "mode": mode or split.get("mode", ""),
        "result_dir": str(model_dir.relative_to(PROJECT)),
        "model_family": fam,
        "model_dir_subname": sub,
        "framing_alias": alias,
        "transport_direction": transport_direction(fam, str(data.get("source", "")), str(data.get("target", ""))),
        "data_path": str(data.get("path", "")),
        "ae_emb_path": str(((data.get("ae_emb") or {}).get("path", "")) if isinstance(data.get("ae_emb"), dict) else ""),
        "condition_var": str(data.get("condition", "")),
        "source": str(data.get("source", "")),
        "target": str(data.get("target", "")),
        "datasplit_name": str(split.get("name", "")),
        "holdout_key": str(holdout_key),
        "holdout_value": str(holdout_value),
        "n_iters": str(training.get("n_iters", "")),
        "batch_size": str(dl.get("batch_size", "")),
        "hidden_units": ",".join(map(str, model.get("hidden_units") or [])),
        "latent_dim": str(model.get("latent_dim", "")),
        "lr": str(optim.get("lr", "")),
        "device": str(cfg.get("device", "")),
        "status": _read_status(model_dir),
        "evals_present": _evals_present(model_dir),
        "preprocessing_pipeline": preprocessing,
        "data_h5ad_format": data_format,
        "train_sbatch": sbatch_train,
        "eval_sbatch": sbatch_eval,
        "analysis_notebooks": notebooks,
        "notes": notes,
    }
    return rec


# ---------------------------------------------------------------------------
# Catalog of every experiment we have on disk. One entry per (result_dir,
# model_subdir) pair. `(...)` means: the row is fully reconstructed by parsing
# the config.yaml in that directory.
#
# Each tuple is: (model_dir, project_phase, group_label, preprocessing,
#                 mode, train_sbatch, eval_sbatch, notebooks, notes, data_format)
# ---------------------------------------------------------------------------
LEGACY_NB = "perturbOT_tutorial.ipynb / cellot/cellot/explore_dataset.ipynb"
SPECIESOT_NB_BASE = "01_data_preprocessing.ipynb, 01.1_hvg_investigation.ipynb"

CATALOG = [
    # ------------------ legacy public crossspecies (rat held out) -------------------
    # cellot/cellot/  (CPU only, the very first fork)
    (LEGACY / "results" / "cross_species_ood",
     "legacy_crossspecies_cpu", "rat-OOD LPS6 (4-species public dataset)",
     "unrelated", "ood", "sbatch/train/train_cellot_ood.sbatch",
     "sbatch/eval/eval_cellot_1000dim_ood.sbatch / eval_cellot_50dim_ood.sbatch",
     "perturbOT_tutorial.ipynb",
     "First CellOT baseline. 100k iters on raw 1000-dim HVG ortholog space (NO scGen). "
     "Reproduces the original CellOT paper toggle_ood split with rat held out from training.",
     "scrna-crossspecies/hvg-top1k-train-only.h5ad"),
    (LEGACY / "results" / "cross_species_ood_scgen",
     "legacy_crossspecies_cpu", "rat-OOD LPS6 (4-species public dataset)",
     "unrelated", "ood", "sbatch/train/train_scgen_ood.sbatch", "",
     "scgen_training_analysis.ipynb",
     "scGen autoencoder for the CPU run. Status='running' because it was cancelled "
     "after eval_loss converged at step 32500 (see research_log_2026-03-15).",
     "scrna-crossspecies/hvg-top1k-train-only.h5ad"),

    # cellot/cellot_gpu/  (the GPU repo fork from March 10)
    (GPU / "results" / "cross_species_ood",
     "legacy_crossspecies_gpu", "rat-OOD LPS6 (4-species public dataset)",
     "unrelated", "ood", "sbatch/train/train_cellot_ood_gpu.sbatch",
     "sbatch/eval/eval_cellot_1000dim_ood.sbatch",
     "scgen_training_analysis.ipynb, 03_cellot_evaluation_analysis.ipynb",
     "GPU re-run of the rat-OOD CellOT baseline. Same hyperparameters as the CPU run "
     "above. Completed 100k iters; cache/status=done.",
     "scrna-crossspecies/hvg-top1k-train-only.h5ad"),
    (GPU / "results" / "cross_species_ood_scgen_gpu",
     "legacy_crossspecies_gpu", "rat-OOD LPS6 (4-species public dataset)",
     "unrelated", "ood", "sbatch/train/train_scgen_ood_gpu.sbatch", "",
     "scgen_training_analysis.ipynb",
     "GPU scGen training. Cancelled mid-run after eval loss plateaued; status='running' "
     "in cache/. Sufficient for downstream CellOT use; race_* and speciesot_cpu/ both "
     "borrowed this checkpoint via the model-scgen symlink.",
     "scrna-crossspecies/hvg-top1k-train-only.h5ad"),
    # `cross_species_ood_cellot_gpu/` is an empty placeholder - never trained
    (GPU / "results" / "cross_species_ood_cellot_gpu",
     "legacy_crossspecies_gpu", "rat-OOD LPS6 (4-species public dataset)",
     "unrelated", "ood", "sbatch/train/train_cellot_ood_gpu.sbatch", "",
     "(none)",
     "Placeholder directory created by sbatch but never populated. No config.yaml, no "
     "cache. Treat as never_started.",
     "scrna-crossspecies/hvg-top1k-train-only.h5ad"),

    # racing experiments to compare partition speed (March 15)
    (GPU / "results" / "race_cpu",
     "racing", "rat-OOD LPS6 (4-species, 10k iter race)", "unrelated", "ood",
     "sbatch/train/racing_cellot/cellot_cpu_shared.sbatch",
     "(internal evals_ood_latent_space + evals_ood_data_space)",
     "scgen_training_analysis.ipynb",
     "CPU race. 10k CellOT iters in 8.5 min on shared partition (19.6 it/s). "
     "Used to demonstrate that scGen-50dim CellOT is trivially fast.",
     "scrna-crossspecies/hvg-top1k-train-only.h5ad"),
    (GPU / "results" / "race_gpu_requeue",
     "racing", "rat-OOD LPS6 (4-species, 10k iter race)", "unrelated", "ood",
     "sbatch/train/racing_cellot/cellot_gpu_requeue.sbatch", "",
     "scgen_training_analysis.ipynb",
     "GPU requeue race. Same 10k iters as race_cpu; comparable wall time. The cellot_gpu.sbatch "
     "script (sbatch/train/racing_cellot/cellot_gpu.sbatch) was submitted to the gpu partition but "
     "stayed pending; we never recorded a separate result_dir for it.",
     "scrna-crossspecies/hvg-top1k-train-only.h5ad"),

    # ------------------ speciesOT iteration 1 (March 18) -------------------
    # broad-T-cell holdout, hvg-top1k.h5ad - WRONG transport direction (human->mouse)
    (GPU / "results" / "speciesot_cpu" / "speciesot_scgen",
     "speciesot_v1_iter1", "Broad T cell (CL:0000084) - iter 1 (REVERSED direction)",
     "stale", "ood", "sbatch/train/train_scgen_speciesot_cpu.sbatch", "",
     "04_heldout_TCell_evaluation.ipynb",
     "Iteration 1 scGen on the small ~12k-cell matched-only dataset. Direction was "
     "human->mouse (reversed; corrected in iteration 2). Overfit fast due to tiny dataset.",
     "speciesot-human-mouse/hvg-top1k.h5ad"),
    (GPU / "results" / "speciesot_cpu" / "speciesot_cellot",
     "speciesot_v1_iter1", "Broad T cell (CL:0000084) - iter 1 (REVERSED direction)",
     "stale", "ood", "sbatch/train/train_cellot_speciesot_cpu.sbatch",
     "sbatch/eval/eval_speciesot_cpu_data.sbatch / eval_speciesot_cpu_latent.sbatch",
     "04_heldout_TCell_evaluation.ipynb",
     "Iteration 1 CellOT (10k iters). Treated as a learning artifact - results "
     "discarded after the direction fix in iteration 2.",
     "speciesot-human-mouse/hvg-top1k.h5ad"),

    # ------------------ speciesOT iteration 2 / Group A (March 25) -------------------
    (GPU / "results" / "speciesot_cd8" / "speciesot_scgen",
     "speciesot_v1_iter2_groupA", "Group A: CD8+ T cell holdout (CL:0000625)",
     "stale", "ood", "sbatch/train/train_scgen_cd8.sbatch", "",
     "05_expanded_training_CD8_holdout.ipynb, 06_cd8_holdout_evaluation.ipynb, "
     "06.1_r2_illustration_full_context_umap.ipynb",
     "scGen autoencoder retrained on the EXPANDED ~106k-cell dataset (excluding CD8). "
     "Reused as encoder by both impact_or/ and cellot/ below. A trimmed mirror of this "
     "directory (config + scalars only, no model.pt) is git-tracked at "
     "speciesOT/baseline/results/speciesot_cd8/speciesot_scgen/.",
     "speciesot-human-mouse/ae_training_expanded_v07.h5ad"),
    (GPU / "results" / "speciesot_cd8" / "impact_or",
     "speciesot_v1_iter2_groupA", "Group A: CD8+ T cell holdout (CL:0000625)",
     "stale", "ood", "sbatch/train/train_cellot_cd8.sbatch  (despite name, IMPACT-OR framing)",
     "sbatch/eval/eval_cd8_ood_dataspace.sbatch",
     "06_cd8_holdout_evaluation.ipynb, 08_cross_experiment_evaluation.ipynb, "
     "12_figure_g_replication.ipynb",
     "IMPACT-OR framing: condition=species, source=mouse, target=human, holdout=CD8 "
     "cell type. The directory name 'impact_or' was the FIRST naming convention; later "
     "phases call this 'speciesot_cellot' or 'swapped_cellot'. A trimmed mirror "
     "(config + evals.csv + imputed.h5ad, no model.pt) is git-tracked at "
     "speciesOT/baseline/results/speciesot_cd8/impact_or/.",
     "speciesot-human-mouse/cd8_holdout_v07.h5ad"),
    (GPU / "results" / "speciesot_cd8" / "cellot",
     "speciesot_v1_iter2_groupA", "Group A: CD8+ T cell holdout (CL:0000625)",
     "stale", "ood", "sbatch/train/train_cellot_cd8_swapped.sbatch",
     "sbatch/eval/eval_cd8_ood_cellot_swapped.sbatch",
     "06_cd8_holdout_evaluation.ipynb, 08_cross_experiment_evaluation.ipynb, "
     "06.5_outlier_cell_investigation.ipynb",
     "CellOT framing (paper-style): condition=cell_type_status, source=non_cd8, "
     "target=cd8, holdout=human species. Same architecture as impact_or above; "
     "only the framing differs. A trimmed mirror (config + evals.csv + imputed.h5ad, "
     "no model.pt) is git-tracked at speciesOT/baseline/results/speciesot_cd8/cellot/.",
     "speciesot-human-mouse/cd8_holdout_swapped_v07.h5ad"),

    # ------------------ Groups B, C, D (April 5) -------------------
    # Group B: CD8 holdout WITHOUT thymocytes in training/eval data
    (GPU / "results" / "speciesot_cd8_nothymo" / "speciesot_scgen",
     "speciesot_v1_groupB", "Group B: CD8+ holdout, thymocytes removed from BOTH",
     "stale", "ood", "sbatch/train/train_scgen_cd8_nothymo.sbatch", "",
     "07_data_prep_all_holdouts.ipynb",
     "scGen for Group B. Training data excludes both CD8 and thymocyte cells.",
     "speciesot-human-mouse/ae_training_cd8_nothymo_v07.h5ad"),
    (GPU / "results" / "speciesot_cd8_nothymo" / "speciesot_cellot",
     "speciesot_v1_groupB", "Group B: CD8+ holdout, thymocytes removed from BOTH",
     "stale", "ood", "sbatch/train/train_impact_cd8_nothymo.sbatch (IMPACT-OR framing)",
     "sbatch/eval/eval_cd8_nothymo_impact.sbatch",
     "07_data_prep_all_holdouts.ipynb, 08_cross_experiment_evaluation.ipynb",
     "IMPACT-OR (mouse->human, holdout=CD8). Note the directory is named "
     "'speciesot_cellot' for IMPACT here, opposite to the toggle_*/ convention.",
     "speciesot-human-mouse/cd8_nothymo_holdout_v07.h5ad"),
    (GPU / "results" / "speciesot_cd8_nothymo" / "speciesot_cellot_swapped",
     "speciesot_v1_groupB", "Group B: CD8+ holdout, thymocytes removed from BOTH",
     "stale", "ood", "sbatch/train/train_cellot_cd8_nothymo.sbatch (CellOT framing)",
     "(implicit data-space eval ran -- see evals_ood_data_space/)",
     "07_data_prep_all_holdouts.ipynb, 08_cross_experiment_evaluation.ipynb",
     "CellOT framing (non_cd8 -> cd8, holdout=human).",
     "speciesot-human-mouse/cd8_nothymo_holdout_swapped_v07.h5ad"),
    # Group C: hold out all T-cell subtypes (CD4 + CD8 + thymocyte)
    (GPU / "results" / "speciesot_tcell_subtypes" / "speciesot_scgen",
     "speciesot_v1_groupC", "Group C: All T-cell subtypes held out (CL:0000624,625,893)",
     "stale", "ood", "sbatch/train/train_scgen_tcell_subtypes.sbatch", "",
     "07_data_prep_all_holdouts.ipynb",
     "scGen excluding CD4, CD8, and thymocytes from autoencoder training.",
     "speciesot-human-mouse/ae_training_tcell_subtypes_v07.h5ad"),
    (GPU / "results" / "speciesot_tcell_subtypes" / "speciesot_cellot",
     "speciesot_v1_groupC", "Group C: All T-cell subtypes held out (CL:0000624,625,893)",
     "stale", "ood", "sbatch/train/train_impact_tcell_subtypes.sbatch (IMPACT-OR framing)",
     "sbatch/eval/eval_tcell_subtypes_impact.sbatch",
     "08_cross_experiment_evaluation.ipynb",
     "IMPACT-OR for the broad T-cell holdout group.",
     "speciesot-human-mouse/tcell_subtypes_holdout_v07.h5ad"),
    (GPU / "results" / "speciesot_tcell_subtypes" / "speciesot_cellot_swapped",
     "speciesot_v1_groupC", "Group C: All T-cell subtypes held out (CL:0000624,625,893)",
     "stale", "ood", "sbatch/train/train_cellot_tcell_subtypes.sbatch (CellOT framing)",
     "sbatch/eval/eval_tcell_subtypes_cellot.sbatch",
     "08_cross_experiment_evaluation.ipynb",
     "CellOT framing (non_tcell_subtype -> tcell_subtype, holdout=human).",
     "speciesot-human-mouse/tcell_subtypes_holdout_swapped_v07.h5ad"),
    # Group D: CD4 holdout
    (GPU / "results" / "speciesot_cd4" / "speciesot_scgen",
     "speciesot_v1_groupD", "Group D: CD4+ T cell holdout (CL:0000624)",
     "stale", "ood", "sbatch/train/train_scgen_cd4.sbatch", "",
     "07_data_prep_all_holdouts.ipynb",
     "scGen excluding CD4 from autoencoder training.",
     "speciesot-human-mouse/ae_training_cd4_v07.h5ad"),
    (GPU / "results" / "speciesot_cd4" / "speciesot_cellot",
     "speciesot_v1_groupD", "Group D: CD4+ T cell holdout (CL:0000624)",
     "stale", "ood", "sbatch/train/train_impact_cd4.sbatch (IMPACT-OR framing)",
     "sbatch/eval/eval_cd4_impact.sbatch",
     "08_cross_experiment_evaluation.ipynb",
     "IMPACT-OR. Group D had only ~96 OOD CD4 cells -- evaluations needed --n_cells 50,80 "
     "override (see research_log_2026-04-20).",
     "speciesot-human-mouse/cd4_holdout_v07.h5ad"),
    (GPU / "results" / "speciesot_cd4" / "speciesot_cellot_swapped",
     "speciesot_v1_groupD", "Group D: CD4+ T cell holdout (CL:0000624)",
     "stale", "ood", "sbatch/train/train_cellot_cd4.sbatch (CellOT framing)",
     "sbatch/eval/eval_cd4_cellot.sbatch",
     "08_cross_experiment_evaluation.ipynb",
     "CellOT framing for Group D.",
     "speciesot-human-mouse/cd4_holdout_swapped_v07.h5ad"),
]


# ------------------ toggle_ood experiments (April 9) -------------------
# 8 holdout groups (T1-T4, M1-M4) x 2 modes (iid/ood) x 3 models (scgen/impact/cellot)
TOGGLE_GROUPS = {
    "t1": "T1 -- CD8 only (CL:0000625)",
    "t2": "T2 -- CD8 + thymocyte (CL:0000625, 893)",
    "t3": "T3 -- All T cell subtypes (CL:0000624, 625, 893)",
    "t4": "T4 -- CD4 only (CL:0000624)",
    "m1": "M1 -- Non-classical monocyte (CL:0000875)",
    "m2": "M2 -- Non-classical + generic (CL:0000875, 576)",
    "m3": "M3 -- All monocyte subtypes (CL:0000875, 860, 2393, 576)",
    "m4": "M4 -- Classical monocyte (CL:0000860)",
}

TOGGLE_NB = ("09_data_prep_toggle_experiments.ipynb, "
             "10_iid_vs_ood_evaluation.ipynb, scripts/generate_toggle_configs.py")

for gk, glab in TOGGLE_GROUPS.items():
    for mode in ("iid", "ood"):
        for sub in ("scgen", "impact", "cellot"):
            train_sbatch = f"sbatch/train/train_toggle_{gk}_{mode}_{sub}.sbatch"
            if sub == "scgen":
                eval_sbatch = ""
                fam_note = "scGen autoencoder for the toggle experiment."
            else:
                eval_sbatch = f"sbatch/eval/eval_toggle_{gk}_{mode}_{sub}.sbatch"
                fam_note = (
                    "IMPACT framing (condition=species, mouse->human, holdout=cell_type)."
                    if sub == "impact"
                    else "CellOT framing (condition=cell_type_status, non_X -> X, holdout=human)."
                )
            CATALOG.append((
                GPU / "results" / f"toggle_{gk}_{mode}" / sub,
                "toggle", glab, "stale", mode, train_sbatch, eval_sbatch, TOGGLE_NB,
                f"toggle_ood split: half of holdout cells form the OOD test set; the other "
                f"half is added to training (mode=iid) or discarded (mode=ood). {fam_note}",
                f"speciesot-human-mouse/toggle_{gk}_*_{mode}_v07.h5ad" if sub == "scgen"
                else f"speciesot-human-mouse/toggle_{gk}_holdout_{'swapped_' if sub=='cellot' else ''}v07.h5ad",
            ))


# ------------------ renorm experiments (April 21) -------------------
# After the preprocessing audit (research_log_2026-04-20), all four Groups A/B/C/D
# were rebuilt with the corrected normalization pipeline (.raw.to_adata() ->
# match cells -> ortholog align -> normalize_total -> log1p, identical for both
# species). Result: 4 groups x 3 models = 12 trainings.
RENORM_GROUPS = {
    "cd8":              ("Renorm Group A: CD8+ T cell holdout (CL:0000625)", "CL:0000625"),
    "cd8_thymo":        ("Renorm Group B: CD8+ holdout, thymocytes excluded", "CL:0000625"),
    "tcell_subtypes":   ("Renorm Group C: All T-cell subtypes (CL:0000624,625,893)", "[0624,0625,0893]"),
    "cd4":              ("Renorm Group D: CD4+ T cell holdout (CL:0000624)", "CL:0000624"),
}
RENORM_NB = ("01.3_data_prep_all_holdouts_renorm.ipynb, 08.1_renorm_vs_stale_comparison.ipynb, "
             "01.4_hvg_flavor_comparison.ipynb, 11_immune_cell_ontology.ipynb, "
             "12_figure_g_replication.ipynb")

for gkey, (glab, _hold) in RENORM_GROUPS.items():
    # sub-dir convention here: scgen/, swapped_cellot/=IMPACT-OR, normal_cellot/=CellOT
    CATALOG.append((
        GPU / "results" / f"renorm_{gkey}" / "scgen",
        "renorm", glab, "renorm", "ood",
        f"sbatch/train/renorm/train_scgen_{gkey}_renorm.sbatch", "", RENORM_NB,
        "scGen autoencoder retrained on the RENORMALIZED data (post Apr-20 audit).",
        f"speciesot-human-mouse-renorm/ae_training_{gkey}_renorm_v07.h5ad",
    ))
    CATALOG.append((
        GPU / "results" / f"renorm_{gkey}" / "swapped_cellot",
        "renorm", glab, "renorm", "ood",
        f"sbatch/train/renorm/train_swapped_cellot_{gkey}_renorm.sbatch",
        f"sbatch/eval/renorm/eval_swapped_cellot_{gkey}_renorm.sbatch", RENORM_NB,
        "IMPACT-OR framing on renormalized data (mouse->human, holdout=cell_type). "
        "WARNING the dir name 'swapped_cellot' here means IMPACT-OR; this is the OPPOSITE "
        "of the older speciesot_cellot_swapped/ which meant CellOT framing.",
        f"speciesot-human-mouse-renorm/{gkey}_holdout_renorm_v07.h5ad",
    ))
    CATALOG.append((
        GPU / "results" / f"renorm_{gkey}" / "normal_cellot",
        "renorm", glab, "renorm", "ood",
        f"sbatch/train/renorm/train_normal_cellot_{gkey}_renorm.sbatch",
        f"sbatch/eval/renorm/eval_normal_cellot_{gkey}_renorm.sbatch", RENORM_NB,
        "CellOT (paper-style) framing on renormalized data (non_X -> X, holdout=human).",
        f"speciesot-human-mouse-renorm/{gkey}_holdout_swapped_renorm_v07.h5ad",
    ))


COLUMNS = [
    "exp_id", "train_finished", "project_phase", "group_label", "mode",
    "result_dir", "model_family", "model_dir_subname", "framing_alias",
    "transport_direction", "data_path", "ae_emb_path", "condition_var",
    "source", "target", "datasplit_name", "holdout_key", "holdout_value",
    "n_iters", "batch_size", "hidden_units", "latent_dim", "lr", "device",
    "status", "evals_present", "preprocessing_pipeline", "data_h5ad_format",
    "train_sbatch", "eval_sbatch", "analysis_notebooks", "notes",
]


def main() -> None:
    rows = []
    for i, entry in enumerate(CATALOG, start=1):
        (model_dir, project_phase, group_label, preprocessing,
         mode, sb_train, sb_eval, nbs, notes, data_format) = entry
        rec = _parse_record(model_dir, project_phase, group_label, preprocessing,
                            mode, sb_train, sb_eval, nbs, notes, data_format)
        rec["exp_id"] = f"E{i:03d}"
        rows.append(rec)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLUMNS})

    print(f"Wrote {len(rows)} experiment rows to {OUT_CSV}")


if __name__ == "__main__":
    main()
