"""Walk the result trees and build ModelRecord/EvalRecord instances.

Two discovery roots, per the hub-design resolution log Q5:
- `cellot/cellot_gpu/results/` (main active tree)
- `speciesOT/baseline/results/` (frozen historical from speciesot_v1 era)

_archive/ subtrees are NOT skipped — per user's "include everything" preference
(Q5 in the resolution log). Only the upstream library's `configs/tasks/*.yaml`
config templates are excluded (those are templates, not trained models).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from speciesOT.hub.catalog import Catalog, EvalRecord, ModelRecord
from speciesOT.hub.readers import (
    headline_metrics,
    mtime,
    parse_evals_subdir_name,
    read_config,
    read_decoded_metrics,
    read_evals_csv,
    read_extended_metrics,
    read_status,
)
from speciesOT.hub.resolve import (
    infer_framing,
    infer_generated_by,
    resolve_family,
)


WORKSPACE_ROOT = Path("/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT")

# Each root has a short tag used as the first segment of run_id so that
# identically-named experiments in two roots remain disambiguated.
DEFAULT_ROOTS: list[tuple[str, Path]] = [
    ("gpu", WORKSPACE_ROOT / "cellot" / "cellot_gpu" / "results"),
    ("baseline", WORKSPACE_ROOT / "speciesOT" / "baseline" / "results"),
]


def iter_model_dirs(root: Path) -> Iterator[Path]:
    """Yield every model dir (= contains config.yaml) under the given root.

    Excludes the upstream library's task templates under
    `cellot/cellot_gpu/configs/`, which also have config.yaml files but are
    templates rather than trained-model directories.
    """
    if not root.exists():
        return
    for config_yaml in root.rglob("config.yaml"):
        model_dir = config_yaml.parent
        if "configs" in model_dir.parts and "results" not in model_dir.parts:
            continue
        yield model_dir


def discover_evals(model_dir: Path) -> list[EvalRecord]:
    """Find every `evals_*/` subdir under model_dir and build an EvalRecord for each."""
    out: list[EvalRecord] = []
    for entry in sorted(model_dir.glob("evals_*")):
        if not entry.is_dir():
            continue
        csv_path = entry / "evals.csv"
        df = read_evals_csv(csv_path)
        if df is None:
            continue
        space, setting = parse_evals_subdir_name(entry.name)
        h_r2, h_mmd, n_cells = headline_metrics(df)
        floor, ceiling, frac_closed, js = read_extended_metrics(entry)
        fgc_dec, fr2_dec, ae_floor, dec_ceiling = read_decoded_metrics(entry)
        imputed = entry / "imputed.h5ad"
        out.append(
            EvalRecord(
                eval_id=entry.name,
                space=space,
                setting=setting,
                eval_dir=entry,
                evals_csv_path=csv_path,
                imputed_h5ad_path=imputed if imputed.exists() else None,
                metrics_full=df,
                headline_r2_means=h_r2,
                headline_mmd=h_mmd,
                n_cells_present=n_cells,
                last_run_at=mtime(csv_path),
                headline_mmd_floor=floor,
                headline_mmd_ceiling=ceiling,
                frac_gap_closed=frac_closed,
                headline_js=js,
                frac_gap_closed_decoded=fgc_dec,
                frac_r2_closed_decoded=fr2_dec,
                mmd_ae_recon_floor=ae_floor,
                mmd_decoded_ceiling=dec_ceiling,
            )
        )
    return out


def _classify_data_source(
    data_path: Optional[str],
) -> tuple[
    Optional[str],  # data_source
    Optional[str],  # normalization
    Optional[bool],  # log1p_applied
    Optional[str],  # hvg_method
    Optional[str],  # hvg_input_layer
]:
    """From config.data.path, infer preprocessing fields.

    Heuristics based on dataset family name + filename pattern. Per
    `scripts/regenerate_hvg_flavor_run_matrix.py` (FLAVOR_INPUT table).
    """
    if not data_path:
        return None, None, None, None, None

    p = str(data_path)

    # Dataset family
    if "speciesot-human-mouse-hvg" in p:
        data_source = "speciesot-human-mouse-hvg"
    elif "speciesot-human-mouse-renorm" in p:
        data_source = "speciesot-human-mouse-renorm"
    elif "speciesot-human-mouse" in p:
        data_source = "speciesot-human-mouse"
    elif "scrna-crossspecies" in p:
        data_source = "scrna-crossspecies"
    else:
        data_source = "unknown"

    # Normalization (heuristic from data_source)
    if data_source in {"speciesot-human-mouse-renorm", "speciesot-human-mouse-hvg"}:
        normalization = "renormed"
    elif data_source == "speciesot-human-mouse":
        normalization = "stale"
    else:
        normalization = "unknown"

    # HVG method (filename pattern; check longest prefixes first)
    hvg_method = None
    if "hvg_pearson_residuals" in p:
        hvg_method = "pearson_residuals"
    elif "hvg_seurat_v3_paper" in p:
        hvg_method = "seurat_v3_paper"
    elif "hvg_seurat_v3" in p:
        hvg_method = "seurat_v3"
    elif "hvg_cell_ranger" in p:
        hvg_method = "cell_ranger"
    elif "hvg_seurat" in p:
        hvg_method = "seurat"

    # HVG input layer: which layer the HVG selection function consumed.
    # (CORRECTED from earlier heuristic; verified against 01.5 §3 / §5 commentary.)
    if hvg_method in {"seurat_v3", "seurat_v3_paper", "pearson_residuals"}:
        hvg_input_layer = "layers['counts']"
    elif hvg_method in {"seurat", "cell_ranger"}:
        hvg_input_layer = "X (log-norm)"
    else:
        hvg_input_layer = None

    # log1p_applied: in the modern hvg-flavor pipeline, `.X` is ALWAYS
    # `log1p(normalize_total(counts))`, regardless of which layer HVG selection
    # consumed. Per notebook 01.5 §3: "Each file carries .X (log1p(normalize_total
    # (counts))) ... .layers['counts'] is dropped before write (downstream training
    # only consumes .X)." So all hvg_flavor data files have log1p_applied=True.
    # Older/legacy data sources (speciesot-human-mouse stale) follow the same
    # convention (scgen training consumes log-normed .X).
    log1p_applied = True if data_source != "unknown" else None

    return data_source, normalization, log1p_applied, hvg_method, hvg_input_layer


def build_record(model_dir: Path, root_tag: str, root: Path) -> Optional[ModelRecord]:
    """Build a ModelRecord from a model dir. Returns None if config.yaml is missing/empty.

    `root_tag` is a short label (e.g. "gpu", "baseline") used as the first
    segment of run_id so identically-named experiments across roots stay disambiguated.
    """
    config_path = model_dir / "config.yaml"
    config = read_config(config_path)
    if not config:
        return None

    # run_id format: "<root_tag>/<path-relative-to-root>"
    # e.g. "gpu/hvg_seurat_d_ood/impact_cellot" or "baseline/speciesot_cd8/cellot"
    try:
        rel = str(model_dir.relative_to(root))
    except ValueError:
        rel = str(model_dir)
    run_id = f"{root_tag}/{rel}" if root_tag else rel

    subdir_name = model_dir.name
    parent_tag = model_dir.parent.name

    family, family_alias_seen = resolve_family(subdir_name, parent_tag)

    # Dig into the config dict (using .get with default {} so missing sections don't crash)
    data = config.get("data", {}) or {}
    model_cfg = config.get("model", {}) or {}
    optim = config.get("optim", {}) or {}
    training = config.get("training", {}) or {}
    dataloader = config.get("dataloader", {}) or {}
    datasplit = config.get("datasplit", {}) or {}

    # Preprocessing
    data_file = data.get("path")
    data_source, normalization, log1p_applied, hvg_method, hvg_input_layer = (
        _classify_data_source(data_file)
    )
    hvg_batch_key = None  # not stored in train-time config; would need data-prep notebook lookup

    # Framing
    condition = data.get("condition")
    source = data.get("source")
    target = data.get("target")
    transport_direction = f"{source} → {target}" if source and target else None
    framing = infer_framing(family, condition, datasplit.get("key"), source, target)

    # Holdout
    holdout = datasplit.get("holdout")
    holdout_cell_types: Optional[list[str]] = None
    holdout_species: Optional[str] = None
    if isinstance(holdout, str):
        if holdout.startswith("CL:"):
            holdout_cell_types = [holdout]
        elif holdout in {"mouse", "human"}:
            holdout_species = holdout
    elif isinstance(holdout, list):
        cl_items = [h for h in holdout if isinstance(h, str) and h.startswith("CL:")]
        if cl_items:
            holdout_cell_types = cl_items

    mode = datasplit.get("mode")
    train_includes_holdout: Optional[bool] = None
    if mode == "iid":
        train_includes_holdout = True
    elif mode == "ood":
        train_includes_holdout = False

    # AE pointer
    ae_emb = data.get("ae_emb") or {}
    ae_emb_path = ae_emb.get("path") if isinstance(ae_emb, dict) else None

    # Architecture (some configs are missing fields; .get returns None gracefully)
    hidden_units = model_cfg.get("hidden_units")
    if hidden_units is not None and isinstance(hidden_units, list):
        try:
            hidden_units = [int(x) for x in hidden_units]
        except (TypeError, ValueError):
            hidden_units = None

    # mtimes
    created_at = mtime(config_path)
    last_modified_candidates = [
        m
        for m in [
            mtime(model_dir / "cache" / "model.pt"),
            mtime(model_dir / "cache" / "last.pt"),
            mtime(config_path),
        ]
        if m is not None
    ]
    last_modified = max(last_modified_candidates) if last_modified_candidates else None

    return ModelRecord(
        run_id=run_id,
        model_dir=model_dir,
        family=family,
        family_alias_seen=family_alias_seen,
        data_source=data_source,
        data_file=data_file,
        normalization=normalization,
        log1p_applied=log1p_applied,
        hvg_method=hvg_method,
        hvg_input_layer=hvg_input_layer,
        hvg_batch_key=hvg_batch_key,
        framing=framing,
        condition=condition,
        source=source,
        target=target,
        transport_direction=transport_direction,
        holdout_cell_types=holdout_cell_types,
        holdout_species=holdout_species,
        train_includes_holdout=train_includes_holdout,
        datasplit_strategy=datasplit.get("name"),
        model_name=model_cfg.get("name"),
        hidden_units=hidden_units,
        latent_dim=model_cfg.get("latent_dim"),
        n_iters=training.get("n_iters"),
        n_inner_iters=training.get("n_inner_iters"),
        batch_size=dataloader.get("batch_size"),
        lr=optim.get("lr"),
        optimizer=optim.get("optimizer"),
        ae_emb_path=ae_emb_path,
        generated_by=infer_generated_by(parent_tag),
        created_at=created_at,
        last_modified=last_modified,
        status=read_status(model_dir),
        evals=discover_evals(model_dir),
    )


def build_catalog(
    roots: Optional[list[tuple[str, Path]]] = None,
) -> Catalog:
    """Walk the given (tag, root) pairs and build a complete catalog.

    Default: DEFAULT_ROOTS — ("gpu", cellot/cellot_gpu/results), ("baseline", speciesOT/baseline/results).
    """
    if roots is None:
        roots = DEFAULT_ROOTS

    records: list[ModelRecord] = []
    walk_root_paths: list[Path] = []
    for root_tag, root in roots:
        walk_root_paths.append(root)
        for model_dir in iter_model_dirs(root):
            rec = build_record(model_dir, root_tag, root)
            if rec is not None:
                records.append(rec)

    return Catalog(
        records=records,
        walk_roots=walk_root_paths,
        discovered_at=datetime.now(),
    )
