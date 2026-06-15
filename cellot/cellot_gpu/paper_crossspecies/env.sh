# Shared paths for paper_crossspecies bundle (source, do not execute).
PAPER_CROSSSPECIES_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CELLOT_GPU="$(cd "${PAPER_CROSSSPECIES_ROOT}/.." && pwd)"
SPECIESOT_ROOT="$(cd "${CELLOT_GPU}/../../" && pwd)"
# GPU training/eval env (torch 2.x + cu121). CPU-only work still uses CellOT via hub.
CELLOT_ENV="${CELLOT_ENV:-CellOT_gpu}"
export PAPER_CROSSSPECIES_ROOT CELLOT_GPU SPECIESOT_ROOT CELLOT_ENV
