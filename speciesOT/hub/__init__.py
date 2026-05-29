"""speciesOT.hub — model-card hub for the speciesOT project.

v0: read-only catalog. Walks `cellot/cellot_gpu/results/` and
`speciesOT/baseline/results/`, builds ModelRecord + EvalRecord
dataclasses with alias resolution, and exposes a CLI (`hub list`,
`hub show <run_id>`).

Design doc: docs/hub_design.md
"""

__version__ = "0.0.1"
