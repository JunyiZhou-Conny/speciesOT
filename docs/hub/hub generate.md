---
title: hub generate
type: hub-command
tags:
  - hub
---

# `./hub generate <spec.yaml>`

Clones an existing model's setup, applies the spec's overrides, and writes **all** the
configs + sbatches to train + evaluate a new experiment cell. Then prints the submit
chain — but **does not run `sbatch`** (you do, on purpose).

```bash
./hub generate specs/m1_modern.yaml --dry-run   # preview, write nothing
./hub generate specs/m1_modern.yaml             # materialize 8 files + model-scgen symlink
```

## What it writes (for tag `<tag>`)

| Path | Purpose |
|---|---|
| `results/<tag>/scgen/config.yaml` | scGen training config |
| `results/<tag>/impact_cellot/config.yaml` | IMPACT training config |
| `results/<tag>/model-scgen` (symlink) | lets [[IMPACT_CellOT]] find its AE sibling ([[scGen]]) |
| `sbatch/train/…` ×2 | train jobs (IMPACT depends on scGen done) |
| `sbatch/eval/…` ×2, `sbatch/eval_dataspace/…` ×2 | latent + data-space evals |

The data-space IMPACT eval **always passes `--embedding ae`** to dodge the §5.5
latent-space silent bug — see [[OOD vs IID evaluation]] for the eval-flag overload.

## Gotchas

- **V100 only** for GPU jobs (`impact_train_device: gpu`); scGen always trains CPU.
- Existing files are skipped unless `--force`.

## Next / related

- Before: [[hub prep]] (build the `.h5ad` first)
- After evals: [[hub metrics]] then [[hub vault]]
- Back to: [[Hub Operations MOC]]
