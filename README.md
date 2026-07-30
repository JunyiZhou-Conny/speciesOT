# speciesOT — cross-species single-cell transport

Predict **human** cells from **mouse** cells with optimal transport in a shared
autoencoder latent space, and measure honestly whether it works.

Two model families are compared on the same cells:

- **IMPACT_CellOT** — a learned ICNN optimal-transport map (the method under test)
- **scGen** — a latent mean shift (the baseline)

The longer-term goal is to compose a *species* transport with a *treatment*
transport, so that unvaccinated mouse cells can predict vaccinated human cells.
Only the species leg is implemented today; see
[`docs/concepts/the four-corner goal.md`](docs/concepts/the%20four-corner%20goal.md).

## Start here

| you want to… | read |
|---|---|
| run a prediction on new mouse data | [`docs/mentor_runbook.md`](docs/mentor_runbook.md) |
| understand the science and the metrics | [`docs/conceptual_framework.md`](docs/conceptual_framework.md) |
| use the CLI | [`docs/hub_usage.md`](docs/hub_usage.md) |
| know the repo-wide rules | [`AGENTS.md`](AGENTS.md) |
| see what is actively in flight | newest file in [`logs/research_logs/`](logs/research_logs/) |

Everything routes through one CLI:

```bash
./hub list         # every trained model discovered on disk
./hub scorecard    # the leaderboard, ranked by the headline metric
./hub show <run_id>
```

`./hub` never submits jobs. It prints the `sbatch` chain and a human submits it.

## Environments

Two conda envs, both required:

| env | why |
|---|---|
| `CellOT` | runs the hub, training, evaluation (torch 1.11) |
| `analysis` | data prep and notebooks (scanpy ≥ 1.12) |

`./hub` activates `CellOT` itself, probing `$HOME` for your conda install. If it
guesses wrong, set `SPECIESOT_CONDA_INIT` to your `etc/profile.d/conda.sh`.

`cellot` is not pip-installed; add it to the path when importing directly:

```bash
export PYTHONPATH=$PWD/cellot/cellot_gpu
```

## Working from a different checkout

Paths are derived from the checkout, so a clone works unchanged. If the code and
the results tree live apart, point the hub at the tree you want:

```bash
export SPECIESOT_ROOT=/path/to/the/results/workspace
```

A few training-time scripts under `scripts/` still hardcode absolute paths. The
mentor-facing path (`./hub`, `scripts/predict_new_input.sh`,
`scripts/eval_external_target.py`) does not.

## What is deliberately not in git

Model checkpoints, datasets, and `.h5ad` payloads are excluded — the results tree
alone is ~2.4 GB. A fresh clone therefore gives you the code but not the inputs.

To run `scripts/predict_new_input.sh` you additionally need, copied out of band
(~34 MB total):

```
cellot/cellot_gpu/results/atlas_full_{seurat_v3,pearson_residuals}/{scgen,impact_cellot}/cache/model.pt
scripts/.biomart_ortholog_cache.csv
scripts/.bcg_symbol_to_ensmusg.csv
```

Both accounts are on the same cluster, so this is one `rsync`.
[`offline_bundle/README.md`](offline_bundle/) has the existing pattern for the
training data.

## Repo map

```
speciesOT/hub/       the CLI and its discovery/catalog/render layers
cellot/cellot_gpu/   trained models, datasets, eval scripts (gitignored payloads)
atlas-paper-vae/     isolated TF VAEArith stack on the atlas cuts
specs/               declarative experiment specs — the source of truth for intent
scripts/             prediction, evaluation, and job-generation scripts
docs/                science, CLI reference, runbooks (also an Obsidian vault)
logs/research_logs/  dated scratch notes; newest = current focus
```

## How results are judged

The headline is `frac_gap_closed_decoded` — the fraction of the mouse→human
distributional gap closed, measured in the frame where the model's output
actually lives. Two guardrails sit beside it: whether the gene means came out
right, and a per-gene Jensen-Shannon divergence.

Read the caveat in `conceptual_framework.md` §5.9 before quoting that fraction.
Its denominator can be small enough to make it unstable, in which case the ratio
of the model's distance to its own reconstruction floor is the statistic to use.

## Related repositories

- **mixhvg-py** — Python port of the [mixhvg](https://github.com/RuzhangZhao/mixhvg)
  ensemble HVG selector, kept separate because it is GPL-3. `hvg_method: mixhvg`
  in a spec requires it; see `docs/hub_usage.md`.
