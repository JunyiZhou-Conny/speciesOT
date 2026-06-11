"""Round-trip the real human (treated) and mouse (control) clouds through the
scGen AE so they live in the SAME decoded space as the model's imputed cloud.

This makes the transport UMAP / MMD comparison apples-to-apples (the §5.9 fix):
  - imputed         = decode(transport(encode(mouse)))   [already decoded]
  - treated_decoded = decode(encode(real human))         [AE-recon of target]
  - control_decoded = decode(encode(mouse))              [AE-recon of source]

Writes eval_clouds_decoded.npz next to eval_clouds.npz.
Run in the CellOT env from cellot_gpu/ with PYTHONPATH=.
"""
from pathlib import Path
import argparse

import numpy as np
import pandas as pd

from cellot.utils.evaluate import load_projectors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evaldir", required=True,
                    help="path to .../impact_cellot/evals_ood_data_space")
    args = ap.parse_args()

    eval_dir = Path(args.evaldir)
    model_dir = eval_dir.parent              # .../impact_cellot
    z = np.load(eval_dir / "eval_clouds.npz", allow_pickle=False)
    control, treated, imputed = z["control"], z["treated"], z["imputed"]
    genes = [str(g) for g in z["genes"]]

    encode, decode = load_projectors(model_dir.parent / "model-scgen", "ae", "data_space")

    def roundtrip(arr):
        df = pd.DataFrame(np.asarray(arr), columns=genes)
        return np.asarray(decode(encode(df)).values, dtype=np.float32)

    treated_dec = roundtrip(treated)
    control_dec = roundtrip(control)

    out = eval_dir / "eval_clouds_decoded.npz"
    np.savez(out, control=control, treated=treated, imputed=imputed,
             treated_decoded=treated_dec, control_decoded=control_dec,
             genes=z["genes"])
    print(f"wrote {out}  shapes: treated_dec={treated_dec.shape} control_dec={control_dec.shape}",
          flush=True)


if __name__ == "__main__":
    main()
