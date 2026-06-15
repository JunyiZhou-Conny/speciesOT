# Plan: H100 / H200 support for CellOT training

**Goal:** Run IMPACT/scGen on `gpu_requeue` H100/H200 nodes (much more capacity than 4× V100),
without breaking existing hub training or eval.

**Blocker today:** `CellOT` env has `torch==1.11.0+cu102` → kernels only for **sm_70 (V100)**.
H100 (sm_90) / H200 (sm_90) fail with `no kernel image is available for execution on the device`.

**Strategy:** New env clone first; validate; then flip hub + paper_crossspecies sbatches.

---

## Status (2026-06-14)

- [x] `CellOT_gpu` env created (pip clone of CellOT + `torch==2.3.1+cu121`)
- [x] `requirements-gpu.txt` written
- [x] Paper + hub sbatches: `--constraint=h100|h200`, `mamba activate CellOT_gpu`
- [x] Production queued: **22619938** / **22619940** (`paper_lps_gpu`)
- [ ] Smoke job **22617403** (`pc_smoke_h100`, 500-iter IMPACT) — validates CUDA on H100
- [ ] Production run completes

If smoke fails, `scancel 22619938 22619940` and debug from `smoke_h100_*.err`.

---

## Phase 0 — Preconditions (no cluster changes)

| Item | Action |
|------|--------|
| Keep V100 path alive | Do **not** delete `CellOT` until `CellOT_gpu` is validated |
| Paper job | `22427475` queued on V100 — can cancel/resubmit after upgrade or let it run |
| Canonical doc | This file + `hub_handoff.md` §8 item 7 |

---

## Phase 1 — Clone env (`CellOT_gpu`)

On login node (or interactive GPU once available):

```bash
mamba create -n CellOT_gpu --clone CellOT
mamba activate CellOT_gpu
```

**Target stack (starting point — tune on cluster):**

| Package | Current `CellOT` | Target `CellOT_gpu` | Notes |
|---------|------------------|---------------------|--------|
| torch | 1.11.0+cu102 | **2.1–2.4 + cu121** (pip or conda) | Must include sm_80/sm_90 wheels |
| numpy | 1.19.5 | **≥1.23, <2** | torch 2.x often needs newer numpy |
| scipy | 1.8.1 | **≥1.10** | check sklearn compatibility |
| scanpy | 1.8.1 | keep 1.8.1 initially | hub eval paths; upgrade only if broken |
| anndata | 0.7.6 | keep unless scanpy forces bump |

Install example (adjust after smoke tests):

```bash
pip install torch==2.3.1 --index-url https://download.pytorch.org/whl/cu121
pip install "numpy>=1.23,<2" "scipy>=1.10"
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

Record final pins in `cellot/cellot_gpu/requirements-gpu.txt` (new file, parallel to `requirements.txt`).

---

## Phase 2 — Smoke tests (login → GPU)

### 2a. CUDA visibility (interactive H100 job, ~5 min)

```bash
srun --partition=gpu_requeue --gres=gpu:1 --constraint=h100 --mem=16G -t 0:10:00 --pty bash
module load python && mamba activate CellOT_gpu
python -c "import torch; x=torch.randn(4,4,device='cuda'); print(torch.__version__, x.device)"
```

Repeat with `--constraint=h200` if cluster feature exists (`sinfo -o %f | grep -i h200`).

### 2b. CellOT import + one training step

```bash
cd cellot/cellot_gpu
export PYTHONPATH=.
python -c "
from cellot.train.train import train_cellot
from cellot.utils import load_config
from pathlib import Path
# use tiny existing config or race config under _archive
"
```

### 2c. Short IMPACT run (paper replication)

Materialize or reuse `results/paper_crossspecies_rat_ood/impact_cellot/config.yaml`, override:

```bash
python scripts/train.py \
  --outdir ./results/_smoke_impact_h100 \
  --config ./results/paper_crossspecies_rat_ood/impact_cellot/config.yaml \
  --config.device cuda \
  --config.training.n_iters 500
```

**Pass criteria:** no CUDA kernel errors; `cache/status` progresses; loss finite.

### 2d. Eval + extended_metrics (one model)

```bash
python scripts/evaluate.py --outdir ... --setting ood --where data_space --embedding ae \
  --n_cells 500 --n_reps 2 --evalprefix evals_smoke
python scripts/extended_metrics.py --outdir ... --setting ood --where data_space --embedding ae \
  --evalprefix evals_smoke --n_cells 500 --n_markers 50
```

### 2e. Regression vs V100 (optional but recommended)

Compare 500-iter IMPACT loss curve or final MMD on frozen v08 OOD cut (same seed) — should be same order of magnitude, not bitwise identical.

---

## Phase 3 — Slurm / constraint policy

### Feature names (verify on cluster)

```bash
sinfo -p gpu_requeue -o "%f" | tr ',' '\n' | grep -iE 'h100|h200|v100' | sort -u
```

### Recommended constraints

| Priority | Constraint | Rationale |
|----------|------------|-----------|
| 1 | `h200` | Often fastest; many nodes on holygpu8a |
| 2 | `h100` | Wide availability |
| 3 | `v100` | Fallback for old env / debugging |

**Do not** submit without constraint to `gpu_requeue` — mixed A100/H100/H200 pool is hard to reason about.

### Code changes after validation

1. `speciesOT/hub/spec.py`: `_GPU_CONSTRAINT = "h100|h200"` or empty + document; or `PAPER_GPU_CONSTRAINT` env var
2. `cellot/cellot_gpu/paper_crossspecies/sbatch/run_full_pipeline_gpu*.sbatch`:
   - Replace `--constraint=v100` with `--constraint=h100` (or `h200` if preferred)
   - Add `#SBATCH --open-mode=append` (already present)
3. `paper_crossspecies/scripts/run_train_gpu.sh`: `mamba activate CellOT_gpu` (or `CELLOT_ENV` env var)
4. `AGENTS.md`: update GPU rule once shipped

### Wrapper option

```bash
# paper_crossspecies/env.sh
CELLOT_ENV="${CELLOT_ENV:-CellOT_gpu}"  # after cutover
```

---

## Phase 4 — Resubmit paper replication

1. `scancel 22427475 22427476` (V100 queue) if still pending
2. Mark rat scGen still `done` (already set)
3. `submit_gpu_remainder.sh --submit` with new sbatch
4. Chain second 72h continuation job

**Expected speedup vs V100:** IMPACT often **3–10×** (H100/H200 + faster memory). Paper remainder (~3×250k + eval) **~6–24h GPU** vs **~1–3 days** on V100.

---

## Phase 5 — Hub cutover (after paper job green)

1. `./hub` wrapper: activate `CellOT_gpu` for GPU sbatches OR pass env in sbatch preamble
2. Re-run one known IMPACT train+eval on v08 m1 OOD (50k iters) vs historical metrics
3. `./hub scorecard` — north-star should remain in same ballpark
4. Update `hub_handoff.md` §8 item 7 → shipped

---

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| numpy/scipy ABI breaks | Clone env; pin versions in `requirements-gpu.txt` |
| scanpy 1.8 + torch 2 conflict | Keep scanpy 1.8; eval only loads h5ad via cellot paths |
| Checkpoint load across torch versions | `torch.load` state_dict usually OK; test loading existing `model.pt` |
| H200 reserved / draining nodes | Prefer `h100`; use `h200` as first choice if `sinfo` shows idle |
| Dual-env confusion | `CellOT` = CPU + legacy V100; `CellOT_gpu` = H100/H200 |
| Training numerics drift | Short regression + full paper eval as acceptance |

---

## Acceptance criteria (definition of done)

- [ ] `CellOT_gpu`: `torch` runs matmul on H100 and H200 interactive nodes
- [ ] 500-iter IMPACT smoke on `paper_crossspecies_rat_ood` config succeeds on GPU
- [ ] `evaluate.py` + `extended_metrics.py` smoke succeeds
- [ ] Paper sbatch uses `h100`/`h200` constraint; no `v100` required
- [ ] `22427475` replacement job completes rat IMPACT → mouse chain (or first 72h chunk + resume)
- [ ] `AGENTS.md` + `hub_handoff.md` updated
- [ ] `requirements-gpu.txt` committed when user requests commit

---

## Suggested timeline

| Phase | Effort |
|-------|--------|
| 1 Clone + pip upgrade | 1–2 h |
| 2 Smoke tests | 2–4 h (incl. queue wait) |
| 3 Slurm + script edits | 1 h |
| 4 Paper resubmit + walltime | 1–2 days compute |
| 5 Hub regression | 4–8 h |

**Critical path:** interactive H100 slot for Phase 2 → everything else is parallelizable.
