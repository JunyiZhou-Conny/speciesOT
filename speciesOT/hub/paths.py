"""Canonical workspace-root and interpreter resolution for the hub.

Every hub module used to hardcode
``/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT``. That is a quiet failure mode
for anyone else: a collaborator who clones the repo elsewhere and runs ``./hub``
does not get an error, they get *someone else's results*, because discovery walks
the absolute path instead of their checkout.

The root is derived from this file's own location, so a clone works with no
configuration. ``SPECIESOT_ROOT`` overrides it for the case where the code and
the results tree genuinely live apart.
"""

from __future__ import annotations

import os
from pathlib import Path

# speciesOT/hub/paths.py -> speciesOT/hub -> speciesOT -> <workspace root>
_DERIVED_ROOT = Path(__file__).resolve().parents[2]


def workspace_root() -> Path:
    """Repo root. Override with SPECIESOT_ROOT."""
    override = os.environ.get("SPECIESOT_ROOT", "").strip()
    return Path(override).expanduser().resolve() if override else _DERIVED_ROOT


WORKSPACE_ROOT = workspace_root()
DOCS_DIR = WORKSPACE_ROOT / "docs"
CELLOT_DIR = WORKSPACE_ROOT / "cellot" / "cellot_gpu"
MODEL_CARDS_DIR = DOCS_DIR / "model_cards"


def env_python_candidates(env_name: str, override_var: str) -> list[str]:
    """Candidate interpreter paths for a conda env, most-specific first.

    Probes the current user's home before falling back to the original author's
    absolute paths, so a collaborator does not have to set anything to get the
    common layouts. ``override_var`` always wins.
    """
    home = Path.home()
    candidates = [os.environ.get(override_var, "")]
    for base in (home / "miniforge3", home / ".conda", home / "miniconda3",
                 home / "anaconda3", home / "mambaforge"):
        candidates.append(str(base / "envs" / env_name / "bin" / "python"))
    # Historical absolute paths, kept last so existing setups keep working.
    candidates += [
        f"/n/home01/jzhou1125/miniforge3/envs/{env_name}/bin/python",
        f"/n/home01/jzhou1125/.conda/envs/{env_name}/bin/python",
    ]
    return candidates
