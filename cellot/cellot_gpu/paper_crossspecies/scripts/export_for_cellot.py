import anndata as ad
import numpy as np
from pathlib import Path

p = Path("datasets/scrna-crossspecies/hvg-top1k-train-only.h5ad")
a = ad.read_h5ad(p)
out = Path("datasets/scrna-crossspecies/_crossspecies_export.npz")
X = a.X
if hasattr(X, "toarray"):
    X = X.toarray()
np.savez_compressed(out, X=X.astype(np.float32))
a.obs.to_csv(out.with_suffix(".obs.csv"))
a.var.to_csv(out.with_suffix(".var.csv"))
a.varm["marker_genes-condition-rank"].to_csv(out.with_suffix(".marker_rank.csv"))
print("exported", out, a.shape)
