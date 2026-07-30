# atlas-paper-vae — Lotfollahi-like TF VAE on Tabula human–mouse (Plan C)

Isolated third stack next to hub AE-scGen and IMPACT_CellOT.

**Fence:** never write  
`cellot/cellot_gpu/results/hvg_pearson_residuals_*_v08_ood/scgen/`.

Design doc: `logs/research_logs/agent_plans_2026-07-21/DELIVERABLE_C_vae_atlas_design.md`  
Intent spec: `specs/atlas_paper_vae_m2_v08.yaml`

## Quick path

```bash
# 1) Dry-run split (analysis env; no TF)
conda run -n analysis python atlas-paper-vae/scripts/00_dry_run_split.py

# 2) Train plan / Phase 2 train (scgen_tf1)
conda activate scgen_tf1
export PYTHONPATH=$PWD/scgen-cellot-ablation/scgen-reproducibility/code:$PYTHONPATH
python atlas-paper-vae/scripts/01_train_vae.py          # plan only
python atlas-paper-vae/scripts/01_train_vae.py --go     # full train
# optional smoke (not a result):
python atlas-paper-vae/scripts/01_train_vae.py --go --smoke

# 3) Eval → metrics.json
python atlas-paper-vae/scripts/02_eval_metrics.py --go

# 4) SLURM chain (prints sbatch; does not submit)
bash atlas-paper-vae/scripts/submit_train.sh
```

## Prediction

`single_species_delta`: δ = mean(z|human, train) − mean(z|mouse, train), applied to OOD mouse, then decode. Honest analogue of hub scGen mean-shift — not Fig.5 two-path.

## Phase 2

Full train → `metrics.json` → metric atlas canvas `atlas-paper-vae-m2-v08-metrics`  
Compare to Plan B AE-scGen on the same v08 OOD cells (`frac_gap_closed_decoded`).
