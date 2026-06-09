"""Experiment specs (v1): declarative cell-level specs + factory.

A spec describes one experiment cell — typically (group, hvg_method, mode) —
that yields **2 trained models** (scGen + IMPACT_CellOT) plus their training
and evaluation sbatches.

Two starting points:
    spec_from_record(rec): reverse-engineer an `ExperimentSpec` from any
        existing ModelRecord. Used by `./hub spec dump <run_id>`.
    load_spec_yaml(path): parse a hand-edited spec YAML.

Materialization:
    generate_artifacts(spec, dry_run=False, force=False) writes:
      - cellot/cellot_gpu/results/<tag>/scgen/config.yaml
      - cellot/cellot_gpu/results/<tag>/impact_cellot/config.yaml
      - cellot/cellot_gpu/results/<tag>/model-scgen → scgen   (symlink)
      - sbatch/train/train_<tag>_{scgen,impact_cellot}.sbatch
      - sbatch/eval/eval_<tag>_{scgen,impact_cellot}.sbatch
      - sbatch/eval_dataspace/eval_<tag>_{scgen,impact_cellot}_dataspace.sbatch

Behavior matches `scripts/generate_hvg_flavor_configs.py` (the script this
factory eventually retires) — same f-string templates, same default
hyperparameters, same sbatch shape. Differences:

  - The IMPACT_CellOT data-space eval now **always** passes `--embedding ae`,
    which fixes the bug documented in `docs/conceptual_framework.md` §5.5.
    The old generator only did this for the m2 cells (--m2-two-flavors run).

  - Every spec carries lineage: `derived_from` if it was cloned from another
    spec or a ModelRecord. The factory injects this into the materialized
    configs as a comment.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

import yaml

from speciesOT.hub.catalog import ModelRecord
from speciesOT.hub.discover import WORKSPACE_ROOT

CELLOT_DIR = WORKSPACE_ROOT / "cellot" / "cellot_gpu"
RESULTS_DIR = CELLOT_DIR / "results"
SBATCH_DIR = WORKSPACE_ROOT / "sbatch"


# ---------------------------------------------------------------------------
# Spec dataclass
# ---------------------------------------------------------------------------

@dataclass
class ExperimentSpec:
    """Declarative description of one experiment cell.

    All fields except `experiment_tag` and `data_file` have defaults that
    match the existing matrix conventions. Override only what's different
    from the canonical setup.
    """

    # Identity
    experiment_tag: str                   # e.g. "hvg_pearson_residuals_m1_ood"
    derived_from: Optional[str] = None    # parent run_id if cloned

    # === Data inputs and provenance ===
    # data_source: the dataset family name (e.g. speciesot-human-mouse-hvg).
    # data_file: relative path under cellot/cellot_gpu/ — the .h5ad the training
    # script actually loads. The remaining fields below document HOW that file
    # was produced from raw inputs. The hub's v1 generator does not currently
    # materialize the file; it records the intent so future-you (or a future
    # `hub prep` milestone) can rebuild the file from the spec.
    data_source: str = "speciesot-human-mouse-hvg"
    data_file: str = ""

    # Source datasets the .h5ad is built from. These are the pre-processed
    # "sampled" files Josh produced (see speciesOT/baseline/analysis/01.5 §1).
    source_datasets: dict = field(default_factory=lambda: {
        "mouse": "/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_muris/sampled_mouse_shared.h5ad",
        "human": "/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_sapiens/sampled_human_shared.h5ad",
    })

    # ENFORCED preprocessing treatment (since 2026-06-05): `./hub prep` keeps only
    # these assays per species and drops the rest. The atlas sources mix platforms
    # (10x droplet vs Smart-seq2 plate-based); the Smart-seq2 minority has a very
    # different expression distribution and was the OOD "scatter" / MMD inflator
    # (see notebook 21 + docs/conceptual_framework.md §5.10). Tokens accept the
    # `chromium_v{2,3}` aliases, the literal `10x 3' v{2,3}` strings, or the EFO
    # ids (see prep.py:_ASSAY_ALIASES). Default = one droplet platform per species:
    # mouse 10x 3' v2, human 10x 3' v3. Leave empty only to deliberately disable
    # the treatment (prep warns loudly).
    assay_filter: dict = field(default_factory=lambda: {
        "mouse": ["chromium_v2"],
        "human": ["chromium_v3"],
    })
    cap_cells_per_type: dict = field(default_factory=lambda: {
        "mouse": 1000,
        "human": 1000,
    })

    # Ortholog mapping (used by 01.5 to align mouse↔human gene symbols).
    ortholog_source: str = "biomart"

    # Use the backed-mode prep path (speciesOT/hub/prep_backed.py) for LARGE source
    # files that can't be full-loaded (e.g. the 43GB tabula_*_all.h5ad full atlas).
    # The default in-memory path (prep.py) is fine for the ~50k sampled_*_shared files.
    source_backed: bool = False

    # HVG selection (the 01.5 stage).
    hvg_method: Optional[str] = None
    hvg_n_top: int = 1000
    hvg_input_layer: Optional[str] = None
    hvg_batch_key: str = "species"

    # Whether the final `.X` is `log1p(normalize_total(counts))`. In the modern
    # pipeline this is always True regardless of hvg_method (per 01.5 §3).
    # Recorded for provenance and to document the contract scgen/IMPACT_CellOT
    # depend on.
    log1p_applied: Optional[bool] = True

    # Framing
    condition_column: str = "condition"
    source: str = "mouse"
    target: str = "human"

    # Holdout
    holdout_cell_types: list[str] = field(default_factory=list)
    holdout_species: Optional[str] = None
    datasplit_strategy: str = "toggle_ood"
    mode: str = "ood"                     # "ood" or "iid"
    test_size: float = 0.2
    random_state: int = 0
    # Stratify the 50/50 ignore/ood split of the holdout pool on this obs column
    # (e.g. "condition" = species) so the OOD subset is balanced. None = the
    # original unstratified behaviour (which drifts, see conceptual_framework §5.7).
    # Setting it renders `stratify: <col>` into the config datasplit block, read by
    # cell.py:split_cell_data_toggle_ood. Opt-in so existing splits are unchanged.
    datasplit_stratify: Optional[str] = None

    # Architecture — scGen
    scgen_hidden_units: list[int] = field(default_factory=lambda: [256, 256])
    scgen_latent_dim: int = 50
    scgen_lr: float = 0.001
    scgen_batch_size: int = 256
    scgen_n_iters: int = 50000

    # Architecture — IMPACT_CellOT
    impact_hidden_units: list[int] = field(default_factory=lambda: [64, 64, 64, 64])
    impact_latent_dim: int = 50
    impact_lr: float = 0.0001
    impact_batch_size: int = 128
    impact_n_iters: int = 50000
    impact_n_inner_iters: int = 10

    # Where IMPACT_CellOT trains: "gpu" (gpu_requeue + V100 constraint, default)
    # or "cpu" (shared partition, --config.device cpu). The model is small enough
    # to train on CPU; use "cpu" to avoid waiting on a scarce compatible GPU.
    # scGen always trains on CPU regardless. See docs/hub_handoff.md §8 for the
    # torch-upgrade follow-up that would widen GPU compatibility.
    impact_train_device: str = "gpu"

    # Eval n_cells for data_space (latent uses defaults from evaluate.py)
    data_space_n_cells: str = "30,50,80"

    # Notes (free-form)
    notes: str = ""


# ---------------------------------------------------------------------------
# Spec <-> YAML
# ---------------------------------------------------------------------------

def write_spec_yaml(spec: ExperimentSpec, path: Path) -> Path:
    """Write a spec to YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(spec)
    # Order top-level keys for readability
    ordered = {}
    key_order = [
        # Identity
        "experiment_tag", "derived_from",
        # Data inputs and provenance
        "data_source", "data_file",
        "source_datasets",
        "assay_filter", "cap_cells_per_type",
        "ortholog_source", "source_backed",
        # HVG selection
        "hvg_method", "hvg_n_top", "hvg_input_layer", "hvg_batch_key",
        "log1p_applied",
        # Framing
        "condition_column", "source", "target",
        # Holdout
        "holdout_cell_types", "holdout_species", "datasplit_strategy",
        "mode", "test_size", "random_state", "datasplit_stratify",
        # Architecture — scGen
        "scgen_hidden_units", "scgen_latent_dim", "scgen_lr",
        "scgen_batch_size", "scgen_n_iters",
        # Architecture — IMPACT_CellOT
        "impact_hidden_units", "impact_latent_dim", "impact_lr",
        "impact_batch_size", "impact_n_iters", "impact_n_inner_iters",
        "impact_train_device",
        # Eval
        "data_space_n_cells",
        # Free-form
        "notes",
    ]
    for k in key_order:
        if k in data:
            ordered[k] = data[k]
    # Append any keys we forgot in the explicit list
    for k, v in data.items():
        if k not in ordered:
            ordered[k] = v

    with open(path, "w") as f:
        yaml.safe_dump(ordered, f, default_flow_style=False, sort_keys=False)
    return path


def load_spec_yaml(path: Path) -> ExperimentSpec:
    """Parse a spec from YAML. Unknown keys are ignored (forward-compat)."""
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    # Filter to known fields
    known = {f.name for f in ExperimentSpec.__dataclass_fields__.values()}
    filtered = {k: v for k, v in data.items() if k in known}
    return ExperimentSpec(**filtered)


def _apply_record_to_scgen_slot(rec: ModelRecord, spec: ExperimentSpec) -> None:
    """Copy a scgen ModelRecord's hyperparameters into the scgen_* slot of spec."""
    if rec.hidden_units:
        spec.scgen_hidden_units = list(rec.hidden_units)
    if rec.latent_dim:
        spec.scgen_latent_dim = rec.latent_dim
    if rec.lr:
        spec.scgen_lr = rec.lr
    if rec.batch_size:
        spec.scgen_batch_size = rec.batch_size
    if rec.n_iters:
        spec.scgen_n_iters = rec.n_iters


def _apply_record_to_impact_slot(rec: ModelRecord, spec: ExperimentSpec) -> None:
    """Copy an impact_cellot ModelRecord's hyperparameters into the impact_* slot."""
    if rec.hidden_units:
        spec.impact_hidden_units = list(rec.hidden_units)
    if rec.latent_dim:
        spec.impact_latent_dim = rec.latent_dim
    if rec.lr:
        spec.impact_lr = rec.lr
    if rec.batch_size:
        spec.impact_batch_size = rec.batch_size
    if rec.n_iters:
        spec.impact_n_iters = rec.n_iters
    if rec.n_inner_iters:
        spec.impact_n_inner_iters = rec.n_inner_iters


def spec_from_record(rec: ModelRecord, sibling: Optional[ModelRecord] = None) -> ExperimentSpec:
    """Reverse-engineer an ExperimentSpec from a ModelRecord (and optional sibling).

    A single ModelRecord describes ONE model (e.g. impact_cellot of some cell),
    but an ExperimentSpec describes the CELL (both scgen + impact_cellot). If a
    `sibling` ModelRecord is provided, its hyperparameters fill the
    counterpart slot. Otherwise we use defaults for the sibling.

    The CLI's spec dump uses build_catalog().find_sibling(rec) to populate the
    sibling automatically when one exists on disk.
    """
    # The experiment tag is the parent dir of the model dir.
    parts = rec.run_id.split("/")
    if len(parts) >= 2:
        # run_id like "gpu/hvg_seurat_d_ood/impact_cellot" — tag is second-to-last
        tag = parts[-2]
    else:
        tag = parts[0]

    spec = ExperimentSpec(
        experiment_tag=tag,
        derived_from=rec.run_id,
        data_source=rec.data_source or "speciesot-human-mouse-hvg",
        data_file=rec.data_file or "",
        hvg_method=rec.hvg_method,
        hvg_input_layer=rec.hvg_input_layer,
        log1p_applied=rec.log1p_applied,
        condition_column=rec.condition or "condition",
        source=rec.source or "mouse",
        target=rec.target or "human",
        holdout_cell_types=rec.holdout_cell_types or [],
        holdout_species=rec.holdout_species,
        datasplit_strategy=rec.datasplit_strategy or "toggle_ood",
        mode="iid" if rec.train_includes_holdout else "ood",
    )

    # Inject hyperparameters from THIS record's model into the matching slot.
    if rec.family == "scgen":
        _apply_record_to_scgen_slot(rec, spec)
    elif rec.family == "impact_cellot":
        _apply_record_to_impact_slot(rec, spec)

    # If we have a sibling, fill the OTHER slot with its actual values so the
    # round-trip is lossless.
    if sibling is not None:
        if sibling.family == "scgen":
            _apply_record_to_scgen_slot(sibling, spec)
        elif sibling.family == "impact_cellot":
            _apply_record_to_impact_slot(sibling, spec)

    return spec


def find_cell_sibling(rec: ModelRecord, all_records: list[ModelRecord]) -> Optional[ModelRecord]:
    """Find the scgen↔impact_cellot sibling of `rec` in the same experiment dir.

    Returns the sibling ModelRecord if found, else None.
    """
    if rec.family not in {"scgen", "impact_cellot"}:
        return None
    want_family = "impact_cellot" if rec.family == "scgen" else "scgen"
    parent = rec.model_dir.parent
    for other in all_records:
        if other.family == want_family and other.model_dir.parent == parent:
            return other
    return None


# ---------------------------------------------------------------------------
# Helpers shared by config + sbatch rendering
# ---------------------------------------------------------------------------

def _holdout_yaml(holdout_list: list[str]) -> str:
    """Render the holdout field as either a single quoted string or a YAML list."""
    if len(holdout_list) == 1:
        return f"  holdout: '{holdout_list[0]}'"
    lines = ["  holdout:"]
    for h in holdout_list:
        lines.append(f"  - '{h}'")
    return "\n".join(lines)


def _hidden_units_yaml(units: list[int]) -> str:
    return "\n".join(f"  - {u}" for u in units)


def _stratify_line(spec: ExperimentSpec) -> str:
    """Render the optional datasplit `stratify:` line (with trailing newline) or ''."""
    return f"  stratify: {spec.datasplit_stratify}\n" if spec.datasplit_stratify else ""


# ---------------------------------------------------------------------------
# Config rendering
# ---------------------------------------------------------------------------

def render_scgen_config(spec: ExperimentSpec) -> str:
    holdout_block = _holdout_yaml(spec.holdout_cell_types) if spec.holdout_cell_types else "  holdout: ~"
    return f"""\
# Auto-generated by speciesOT.hub.spec
# derived_from: {spec.derived_from or '(fresh)'}
data:
  condition: {spec.condition_column}
  path: {spec.data_file}
  source: {spec.source}
  target: {spec.target}
  type: cell
dataloader:
  batch_size: {spec.scgen_batch_size}
  shuffle: true
datasplit:
  name: {spec.datasplit_strategy}
  key: cell_type_ontology_term_id
{holdout_block}
  mode: {spec.mode}
  groupby: condition
  random_state: {spec.random_state}
  test_size: {spec.test_size}
{_stratify_line(spec)}device: cuda
model:
  beta: 0.0
  dropout: 0.1
  hidden_units:
{_hidden_units_yaml(spec.scgen_hidden_units)}
  latent_dim: {spec.scgen_latent_dim}
  name: scgen
optim:
  lr: {spec.scgen_lr}
  optimizer: Adam
  weight_decay: 1.0e-05
scheduler:
  gamma: 0.5
  step_size: 100000
training:
  cache_freq: 5000
  eval_freq: 1000
  logs_freq: 100
  n_iters: {spec.scgen_n_iters}
"""


def render_impact_config(spec: ExperimentSpec) -> str:
    holdout_block = _holdout_yaml(spec.holdout_cell_types) if spec.holdout_cell_types else "  holdout: ~"
    return f"""\
# Auto-generated by speciesOT.hub.spec
# derived_from: {spec.derived_from or '(fresh)'}
data:
  ae_emb:
    path: ./results/{spec.experiment_tag}/scgen/
  condition: {spec.condition_column}
  path: {spec.data_file}
  source: {spec.source}
  target: {spec.target}
  type: cell
dataloader:
  batch_size: {spec.impact_batch_size}
  shuffle: true
datasplit:
  name: {spec.datasplit_strategy}
  key: cell_type_ontology_term_id
{holdout_block}
  mode: {spec.mode}
  groupby: condition
  random_state: {spec.random_state}
  test_size: {spec.test_size}
{_stratify_line(spec)}device: cuda
model:
  g:
    fnorm_penalty: 1
  hidden_units:
{_hidden_units_yaml(spec.impact_hidden_units)}
  kernel_init_fxn:
    b: 0.1
    name: uniform
  latent_dim: {spec.impact_latent_dim}
  name: cellot
  softplus_W_kernels: false
optim:
  beta1: 0.5
  beta2: 0.9
  lr: {spec.impact_lr}
  optimizer: Adam
  weight_decay: 0
training:
  cache_freq: 1000
  eval_freq: 250
  logs_freq: 50
  n_inner_iters: {spec.impact_n_inner_iters}
  n_iters: {spec.impact_n_iters}
"""


# ---------------------------------------------------------------------------
# Sbatch rendering
# ---------------------------------------------------------------------------

_PREAMBLE = f"""\
cd {CELLOT_DIR}/

module load python
mamba activate CellOT

# The cellot package is not pip-installed in the CellOT env; put cellot_gpu on
# the path so `import cellot` resolves to this tree (not the empty outer
# namespace package one dir up).
export PYTHONPATH={CELLOT_DIR}:$PYTHONPATH"""


# The CellOT env ships torch 1.11+cu102, whose kernels only support up to
# compute capability sm_70. Newer cards on gpu_requeue (A40/A100/A6000/H100,
# sm_80+) raise "no kernel image is available for execution on the device". Pin
# GPU jobs to V100 nodes (sm_70 == feature `v100` / `cc7.0`) so training can't
# land on an incompatible card. Override/clear if torch is ever upgraded.
_GPU_CONSTRAINT = "v100"


def _sbatch_header(jobname: str, time: str, partition: str, mem: str,
                   outdir: Path, log_prefix: str, gres: Optional[str] = None) -> str:
    lines = [
        "#!/bin/bash",
        f"#SBATCH -J {jobname}",
        "#SBATCH -c 4",
        f"#SBATCH -t {time}",
        f"#SBATCH -p {partition}",
    ]
    if gres:
        lines.append(f"#SBATCH --gres={gres}")
        if _GPU_CONSTRAINT:
            lines.append(f"#SBATCH --constraint={_GPU_CONSTRAINT}")
    lines += [
        f"#SBATCH --mem={mem}",
        f"#SBATCH -o {outdir}/{log_prefix}_%j.out",
        f"#SBATCH -e {outdir}/{log_prefix}_%j.err",
    ]
    return "\n".join(lines)


def render_train_sbatch(spec: ExperimentSpec, model_dir: str, gpu: bool = False) -> str:
    tag = spec.experiment_tag
    out_sub = RESULTS_DIR / tag / model_dir
    short_flavor = (spec.hvg_method or "exp")[:2]
    suffix = "imp" if model_dir == "impact_cellot" else "sg"
    short = f"{short_flavor}_{tag.split('_')[-2] if '_' in tag else tag}_{spec.mode}_{suffix}"

    # IMPACT_CellOT can train on GPU or CPU per spec.impact_train_device; scGen
    # always trains on CPU. We pass --config.device explicitly so the run uses
    # the intended device regardless of what's baked into config.yaml.
    device_override = ""
    if model_dir == "impact_cellot":
        if spec.impact_train_device == "cpu":
            gpu = False
            device_override = " \\\n    --config.device cpu"
        else:
            gpu = True
            device_override = " \\\n    --config.device cuda"

    # IMPACT is the heavy run (adversarial inner loop), so give it the longer
    # wall time even on CPU; scGen's autoencoder is quick.
    is_impact = model_dir == "impact_cellot"
    walltime = "12:00:00" if (gpu or is_impact) else "4:00:00"
    header = _sbatch_header(
        short,
        walltime,
        "gpu_requeue" if gpu else "shared",
        "32G",
        out_sub,
        "train",
        gres="gpu:1" if gpu else None,
    )
    return f"""{header}

{_PREAMBLE}

python ./scripts/train.py \\
    --outdir ./results/{tag}/{model_dir} \\
    --config ./results/{tag}/{model_dir}/config.yaml{device_override}
"""


def render_eval_latent_sbatch(spec: ExperimentSpec, model_dir: str) -> str:
    """Latent-space eval. scgen needs --embedding ae; impact_cellot does NOT
    (impact + latent + ae triggers a column-mismatch assertion in evaluate.py).
    Per docs/conceptual_framework.md §5.5.
    """
    tag = spec.experiment_tag
    out_sub = RESULTS_DIR / tag / model_dir
    short_flavor = (spec.hvg_method or "exp")[:2]
    suffix = "eimp" if model_dir == "impact_cellot" else "esg"
    short = f"{short_flavor}_{tag.split('_')[-2] if '_' in tag else tag}_{spec.mode}_{suffix}"
    header = _sbatch_header(short, "1:00:00", "shared", "32G", out_sub, "eval")

    extra = " --embedding ae" if model_dir == "scgen" else ""
    return f"""{header}

{_PREAMBLE}

python ./scripts/evaluate.py \\
    --outdir ./results/{tag}/{model_dir} \\
    --setting ood \\
    --where latent_space{extra}
"""


def render_eval_dataspace_sbatch(spec: ExperimentSpec, model_dir: str) -> str:
    """Data-space eval. impact_cellot needs --embedding ae or it silently
    becomes a latent-space eval (the bug from §5.5). scgen doesn't need it
    but doesn't hurt either; we omit for parity with the existing convention.
    """
    tag = spec.experiment_tag
    out_sub = RESULTS_DIR / tag / model_dir
    short_flavor = (spec.hvg_method or "exp")[:2]
    suffix = "imds" if model_dir == "impact_cellot" else "scds"
    short = f"{short_flavor}_{tag.split('_')[-2] if '_' in tag else tag}_{spec.mode}_{suffix}"
    header = _sbatch_header(short, "1:00:00", "shared", "32G", out_sub, "eval_dataspace")

    emb_line = "    --embedding ae \\\n" if model_dir == "impact_cellot" else ""
    return f"""{header}

{_PREAMBLE}

python ./scripts/evaluate.py \\
    --outdir ./results/{tag}/{model_dir} \\
    --setting ood \\
    --where data_space \\
{emb_line}    --n_cells {spec.data_space_n_cells} \\
    --evalprefix evals_ood_data_space
"""


# ---------------------------------------------------------------------------
# Materialization
# ---------------------------------------------------------------------------

@dataclass
class GenerationPlan:
    """What `generate_artifacts(spec)` will (or did) write."""
    written: list[Path] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)
    symlinks: list[tuple[Path, str]] = field(default_factory=list)


def _maybe_write(path: Path, content: str, dry_run: bool, force: bool,
                 plan: GenerationPlan) -> None:
    if path.exists() and not force:
        plan.skipped.append((path, "exists (use --force to overwrite)"))
        return
    if dry_run:
        plan.written.append(path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    plan.written.append(path)


def _maybe_symlink(link: Path, target: str, dry_run: bool, force: bool,
                   plan: GenerationPlan) -> None:
    if link.exists() or link.is_symlink():
        if not force:
            plan.skipped.append((link, "symlink exists (use --force to overwrite)"))
            return
        if not dry_run:
            link.unlink()
    if dry_run:
        plan.symlinks.append((link, target))
        return
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target)
    plan.symlinks.append((link, target))


def generate_artifacts(spec: ExperimentSpec, dry_run: bool = False,
                       force: bool = False) -> GenerationPlan:
    """Materialize all configs + sbatches from a spec.

    Returns a GenerationPlan listing what was (or would have been) written.
    Existing files are skipped unless force=True.
    """
    plan = GenerationPlan()
    tag = spec.experiment_tag
    exp_dir = RESULTS_DIR / tag

    # Result dirs (scgen + impact_cellot) + the model-scgen symlink.
    scgen_dir = exp_dir / "scgen"
    impact_dir = exp_dir / "impact_cellot"
    if not dry_run:
        scgen_dir.mkdir(parents=True, exist_ok=True)
        impact_dir.mkdir(parents=True, exist_ok=True)

    # Configs.
    _maybe_write(scgen_dir / "config.yaml", render_scgen_config(spec),
                 dry_run, force, plan)
    _maybe_write(impact_dir / "config.yaml", render_impact_config(spec),
                 dry_run, force, plan)

    # model-scgen symlink contract.
    _maybe_symlink(exp_dir / "model-scgen", "scgen", dry_run, force, plan)

    # Training sbatches.
    train_dir = SBATCH_DIR / "train"
    _maybe_write(
        train_dir / f"train_{tag}_scgen.sbatch",
        render_train_sbatch(spec, "scgen", gpu=False),
        dry_run, force, plan,
    )
    _maybe_write(
        train_dir / f"train_{tag}_impact_cellot.sbatch",
        render_train_sbatch(spec, "impact_cellot"),
        dry_run, force, plan,
    )

    # Latent-space eval sbatches.
    eval_dir = SBATCH_DIR / "eval"
    _maybe_write(
        eval_dir / f"eval_{tag}_scgen.sbatch",
        render_eval_latent_sbatch(spec, "scgen"),
        dry_run, force, plan,
    )
    _maybe_write(
        eval_dir / f"eval_{tag}_impact_cellot.sbatch",
        render_eval_latent_sbatch(spec, "impact_cellot"),
        dry_run, force, plan,
    )

    # Data-space eval sbatches.
    eval_ds_dir = SBATCH_DIR / "eval_dataspace"
    _maybe_write(
        eval_ds_dir / f"eval_{tag}_scgen_dataspace.sbatch",
        render_eval_dataspace_sbatch(spec, "scgen"),
        dry_run, force, plan,
    )
    _maybe_write(
        eval_ds_dir / f"eval_{tag}_impact_cellot_dataspace.sbatch",
        render_eval_dataspace_sbatch(spec, "impact_cellot"),
        dry_run, force, plan,
    )

    return plan


def render_submission_chain(spec: ExperimentSpec) -> str:
    """Print the recommended sbatch invocation chain with afterok deps.

    Doesn't actually submit — just emits the commands the user can copy-paste.
    Mirrors the chain in `sbatch/submit_m2_twoflavors_pipeline.sh`.
    """
    tag = spec.experiment_tag
    lines = [
        f"# Recommended submission chain for {tag} (does not run sbatch — copy-paste manually):",
        "",
        f"cd {WORKSPACE_ROOT}",
        f"SG=$(sbatch --parsable sbatch/train/train_{tag}_scgen.sbatch)",
        f"IMP=$(sbatch --parsable --dependency=afterok:${{SG}} sbatch/train/train_{tag}_impact_cellot.sbatch)",
        f"EV_SG=$(sbatch --parsable --dependency=afterok:${{SG}} sbatch/eval/eval_{tag}_scgen.sbatch)",
        f"EV_IM=$(sbatch --parsable --dependency=afterok:${{IMP}} sbatch/eval/eval_{tag}_impact_cellot.sbatch)",
        f"DS_SG=$(sbatch --parsable --dependency=afterok:${{SG}} sbatch/eval_dataspace/eval_{tag}_scgen_dataspace.sbatch)",
        f"DS_IM=$(sbatch --parsable --dependency=afterok:${{IMP}} sbatch/eval_dataspace/eval_{tag}_impact_cellot_dataspace.sbatch)",
        f'echo "scgen=$SG impact=$IMP eval_scgen=$EV_SG eval_imp=$EV_IM dataspace_scgen=$DS_SG dataspace_imp=$DS_IM"',
    ]
    return "\n".join(lines)
