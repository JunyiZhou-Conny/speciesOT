# Paper cross-species LPS replication (Bunne et al. 2023)

Standalone replication bundle for the **original Hagai/scGen scrna-crossspecies dataset**
(`datasets/scrna-crossspecies/hvg-top1k-train-only.h5ad`). Species holdout via CellOT
`toggle_ood` — **not** routed through `./hub prep` / `./hub generate`.

## Layout

| Path | Purpose |
|------|---------|
| `scripts/` | prep, setup, train (CPU/GPU), eval, collect, submit helpers |
| `sbatch/` | Slurm wrappers (full pipeline, per-model, eval) |
| `specs/` | Provenance YAML (intent only; not hub specs) |
| `../results/paper_crossspecies_*` | Active trained models + eval outputs |
| `../results/paper_crossspecies/_logs/` | Pipeline Slurm logs, failed standalone jobs |
| `../results/_archive/scrna_crossspecies_pre_paper/` | Pre-paper exploratory runs (Mar 2026) |

## Results layout

**Canonical (do not rename while training):**

- `results/paper_crossspecies_rat_ood/` — rat holdout
- `results/paper_crossspecies_mouse_ood/` — mouse holdout

Each contains `scgen/`, `impact_cellot/`, `model-scgen` symlink. IMPACT configs reference
`./results/paper_crossspecies_*_ood/scgen/` for the AE.

**Logs:** `results/paper_crossspecies/_logs/pipeline/` and `failed_jobs/`

**Archived:** `results/_archive/scrna_crossspecies_pre_paper/` — old `cross_species_ood*`,
`race_*` benchmark runs (hub: `gpu/_archive/scrna_crossspecies_pre_paper/...`).


- **Train/eval:** this bundle (CellOT scripts + sbatch).
- **After eval:** optional `./hub metrics gpu/paper_crossspecies_{rat,mouse}_ood/{scgen,impact_cellot}`
  for decoded sidecars and scorecard discovery.

## Quick start

```bash
# Data (analysis env)
mamba activate analysis
python paper_crossspecies/scripts/prep_data.py --backup ...

# Materialize configs + per-model sbatches
python paper_crossspecies/scripts/setup.py --holdout rat --holdout mouse

# CPU full pipeline
sbatch paper_crossspecies/sbatch/run_full_pipeline.sbatch

# GPU remainder (after rat scGen on CPU, or --queue-now)
paper_crossspecies/scripts/submit_gpu_remainder.sh --queue-now

# Summarize paper metrics table
python paper_crossspecies/scripts/collect_results.py
```

Paper eval: `data_space`, `--n_markers 50`, `--n_cells 500,1000`, iid + ood, 250k iters.

**H100/H200:** blocked by torch 1.11 in `CellOT` — see [`GPU_UPGRADE.md`](GPU_UPGRADE.md).
