import anndata as ad
import numpy as np
import pandas as pd
from pathlib import Path

base = Path("datasets/scrna-crossspecies")
z = np.load(base / "_crossspecies_export.npz", allow_pickle=True)
obs = pd.read_csv(base / "_crossspecies_export.obs.csv", index_col=0)
var = pd.read_csv(base / "_crossspecies_export.var.csv", index_col=0)
a = ad.AnnData(X=z["X"], obs=obs, var=var)
a.varm["marker_genes-condition-rank"] = pd.read_csv(
    base / "_crossspecies_export.marker_rank.csv", index_col=0,
)
out = base / "hvg-top1k-train-only.h5ad"
a.write_h5ad(out)
ad.read_h5ad(out)
print("cellot read ok", out, a.shape)
