# Offline data bundle (Tier 1 + Tier 2)

Symlinks on the cluster — **copy to your laptop before the outage** with `-L` so
real files are transferred (not broken symlinks).

**Total size:** ~778 MB (6 `.h5ad` files).

## Contents

### Tier 1 — cross-species / scGen / Bunne LPS

| File | Cells × genes | Notes |
|------|----------------|-------|
| `train_species.h5ad` | 62,114 × 6,619 | scGen canonical train split |
| `valid_species.h5ad` | 15,528 × 6,619 | scGen valid split (77,642 total) |
| `hvg-top1k-train-only.6619-backup.h5ad` | 62,114 × 6,619 | Same bytes as `train_species` on this cluster |
| `hvg-top1k-train-only.h5ad` | 62,114 × 1,000 | CellOT/Bunne 1000 HVG matrix |

### Tier 2 — notebook 21 (v07 / v08 imbalance)

| File | Notes |
|------|-------|
| `hvg_pearson_residuals_m1_v07.h5ad` | m1 v07 cut |
| `hvg_pearson_residuals_m1_v08.h5ad` | m1 v08 cut (assay-aware prep) |

Checksums: see `offline_data_manifest.txt` at repo root.

## Copy to laptop (run on your Mac, VPN on)

```bash
LOCAL=~/speciesOT_offline_$(date +%Y%m%d)
mkdir -p "$LOCAL"

rsync -avL --progress \
  jzhou1125@login.rc.fas.harvard.edu:/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/offline_bundle/ \
  "$LOCAL/offline_bundle/"

# Code (no datasets/results)
rsync -av --progress \
  jzhou1125@login.rc.fas.harvard.edu:/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/ \
  "$LOCAL/speciesOT/" \
  --exclude 'cellot/cellot_gpu/datasets/' \
  --exclude 'cellot/cellot_gpu/results/' \
  --exclude 'offline_bundle/tier*/' \
  --exclude '.git/' \
  --exclude '__pycache__/' \
  --exclude '.ipynb_checkpoints/'
```

Verify after copy:

```bash
cd "$LOCAL/speciesOT"
sha256sum -c offline_data_manifest.txt
```

(`sha256sum -c` expects paths relative to repo root; run from `speciesOT` and adjust
manifest paths or verify manually against `offline_data_manifest.txt`.)

## Local notebook paths

Point notebooks at your offline copy, e.g.:

```python
from pathlib import Path
OFFLINE = Path.home() / "speciesOT_offline_20260614" / "offline_bundle"
H5_CROSS = OFFLINE / "tier1_crossspecies/hvg-top1k-train-only.h5ad"
H5_V08 = OFFLINE / "tier2_hub_v08/hvg_pearson_residuals_m1_v08.h5ad"
```

Env: `conda activate analysis` (scanpy ≥ 1.12). Training / `./hub prep` need the cluster.
