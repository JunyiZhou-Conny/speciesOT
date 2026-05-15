# autospeciesOT

Autonomous experimentation for cross-species cell transport models, inspired by
[karpathy/autoresearch](https://github.com/karpathy/autoresearch).

Instead of iterating on LLM architectures, we iterate on **data preprocessing
and cell type holdout configurations** for CellOT/IMPACT models that transport
gene expression across species (mouse → human).

## How it works

Three files matter:

- **`program.md`** — instructions for the AI agent. Defines the search space,
  experiment loop, and keep/discard rules. Edited by the human.
- **`run_experiment.py`** — single entry-point script. Takes a config, runs
  data prep → scGen training → CellOT/IMPACT training → evaluation, prints
  summary metrics. Not modified by the agent.
- **`results.tsv`** — log of all experiments. Appended by the agent.

## Quick start

```bash
# Activate the CellOT environment
module load python        # (Harvard cluster only)
mamba activate CellOT

# Run the baseline experiment
python run_experiment.py \
    --tag baseline_cd8 \
    --holdout CL:0000625 \
    --model-framing impact \
    --scgen-iters 50000 \
    --cellot-iters 50000

# Run with thymocyte exclusion
python run_experiment.py \
    --tag cd8_no_thymo \
    --holdout CL:0000625 \
    --also-exclude CL:0000893 \
    --model-framing impact \
    --scgen-iters 50000 \
    --cellot-iters 50000
```

## Running the agent

Point your AI agent at this repo and prompt:

```
Read program.md and let's kick off experiments. Do the setup first.
```

## Project structure

```
program.md           — agent instructions (human edits this)
run_experiment.py    — experiment runner (do not modify)
results.tsv          — experiment log (agent appends)
experiments/         — per-experiment outputs (data, checkpoints, evals)
```

## Requirements

- CellOT conda environment with PyTorch, scanpy, anndata
- The cellot codebase at ../cellot/cellot_gpu/
- Pre-prepared datasets at ../cellot/cellot_gpu/datasets/speciesot-human-mouse/

## Timing

| Step | Wall clock |
|------|-----------|
| Data preparation | ~1 min |
| scGen training (50K iters) | ~37 min |
| CellOT/IMPACT training (50K iters) | ~43 min |
| Evaluation | ~2 min |
| **Total (with scGen retrain)** | **~83 min** |
| **Total (scGen cached)** | **~46 min** |
