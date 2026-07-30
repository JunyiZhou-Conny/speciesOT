"""Hub entry points for the cross-species LPS controlled studies.

This module keeps the legacy TensorFlow scGen replication and the new frozen-AE
ICNN-OT sweeps behind the repository's ``./hub`` safety boundary.  Generation
never submits Slurm jobs; it prints explicit commands for human review.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

from speciesOT.hub.paths import WORKSPACE_ROOT as WORKSPACE  # noqa: E402
AUTO = WORKSPACE / "scgen-cellot-autoresearch"
ICNN_SCRIPT = AUTO / "ae_study" / "icnn_ot_sweep.py"
ICNN_WORKER = AUTO / "slurm" / "icnn_ot_experiment.sbatch"
ABLATION = WORKSPACE / "scgen-cellot-ablation"
SCGEN_EVAL = WORKSPACE / "sbatch" / "lps" / "scgen_paper_eval.sbatch"
SCGEN_AUDIT = WORKSPACE / "sbatch" / "lps" / "scgen_paper_audit.sbatch"
SCGEN_AE_STUDY = ABLATION / "scripts" / "09_stage0_ae_followup_study.py"
SCGEN_AE_WORKER = WORKSPACE / "sbatch" / "lps" / "scgen_ae_followup.sbatch"
SCGEN_AE_SPEC = WORKSPACE / "specs" / "lps_scgen_ae_followup.yaml"
STUDY_SPEC = WORKSPACE / "specs" / "lps_icnn_ae_study.yaml"


def _run_icnn(mode: str, round_number: int) -> int:
    command = [
        sys.executable,
        str(ICNN_SCRIPT),
        mode,
        "--round",
        str(round_number),
    ]
    process = subprocess.run(command, cwd=AUTO)
    return process.returncode


def icnn_generate(round_number: int, concurrency: int = 4) -> int:
    rc = _run_icnn("generate", round_number)
    if rc:
        return rc

    manifest = AUTO / "results" / "logs" / f"icnn_ot_round{round_number}_seed0.manifest"
    configs = [line for line in manifest.read_text().splitlines() if line.strip()]
    print()
    if not configs:
        print(f"[hub] ICNN-OT round {round_number}: no pending runs.")
        print(f"[hub] summarize: ./hub lps icnn-summarize --round {round_number}")
        return 0

    print(
        f"[hub] ICNN-OT round {round_number}: {len(configs)} pending GPU jobs "
        f"(max concurrency {concurrency})."
    )
    print("[hub] Review, then submit manually:")
    print(
        "  sbatch "
        f"--array=1-{len(configs)}%{int(concurrency)} "
        f"--export=ALL,AR_MANIFEST={manifest.resolve()} "
        f"{ICNN_WORKER.resolve()}"
    )
    print("[hub] The hub did not submit anything.")
    return 0


def icnn_summarize(round_number: int) -> int:
    return _run_icnn("summarize", round_number)


def scgen_paper_generate() -> int:
    with open(STUDY_SPEC) as handle:
        spec = yaml.safe_load(handle)["paper_scgen"]
    data = WORKSPACE / spec["data_file"]
    prefix = WORKSPACE / spec["checkpoint_prefix"]
    required = [data, prefix.with_suffix(".index"), prefix.with_suffix(".data-00000-of-00001")]
    missing = [path for path in required if not path.exists()]
    if missing:
        print("[hub] scGen paper replication is missing required artifacts:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        return 1

    training_log = prefix.parent / "training_log.csv"
    epochs = 0
    if training_log.exists():
        epochs = max(0, len(training_log.read_text().splitlines()) - 1)
    print(
        "[hub] Found the paper-faithful TensorFlow checkpoint "
        f"({epochs} logged epochs) and {int(spec['genes']):,}-gene Hagai data."
    )
    print("[hub] The next step is evaluation with the shared three-round metrics.")
    print("[hub] Review, then submit manually:")
    print(f"  sbatch {SCGEN_EVAL.resolve()}")
    print("[hub] The hub did not submit anything.")
    return 0


def scgen_paper_audit_generate() -> int:
    """Validate Stage-0 inputs and print the no-retraining audit sbatch."""
    with open(STUDY_SPEC) as handle:
        spec = yaml.safe_load(handle)["paper_scgen"]
    data = WORKSPACE / spec["data_file"]
    prefix = WORKSPACE / spec["checkpoint_prefix"]
    stage0 = ABLATION / "results" / "stage0"
    required = [
        data,
        prefix.with_suffix(".index"),
        prefix.with_suffix(".data-00000-of-00001"),
        stage0 / "metrics.json",
        ABLATION / "scripts" / "04_stage0_fig5_eval.py",
        ABLATION / "scripts" / "05_stage0_identity_audit.py",
        ABLATION / "scripts" / "06_stage0_identity_plots.py",
        SCGEN_AUDIT,
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        print("[hub] scGen Stage-0 audit is missing required artifacts:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        return 1

    print(
        "[hub] Stage-0 audit inputs are ready: "
        f"{int(spec['genes']):,} genes, held out {spec['held_out']}, "
        "existing TensorFlow checkpoint (no retraining)."
    )
    print(
        "[hub] The job rechecks all-gene + top-100 DEG replication, then writes "
        "baseline-calibrated identity sidecars and figures."
    )
    print("[hub] Review, then submit manually:")
    print(f"  sbatch {SCGEN_AUDIT.resolve()}")
    print("[hub] The hub did not submit anything.")
    return 0


def _ae_followup_gate_ok(round_number: int) -> bool:
    """Round 3 requires a completed Round-1 decision artifact on disk."""
    if round_number != 3:
        return True
    decision = (
        ABLATION / "results" / "stage0_ae_followup" / "round1_decision.json"
    )
    if not decision.exists():
        print(
            "[hub] Round 3 requires round1_decision.json; run "
            "./hub lps scgen-ae-followup-summarize --round 1 first.",
            file=sys.stderr,
        )
        return False
    import json

    if not json.loads(decision.read_text()).get("complete"):
        print("[hub] Round 1 is not complete; refusing Round 3.", file=sys.stderr)
        return False
    return True


def scgen_ae_followup_generate(round_number: int, concurrency: int = 2) -> int:
    """Generate one bounded AE follow-up round and print its submission."""
    if round_number == 2:
        print(
            "[hub] Round 2 (capacity) is marked skipped in the spec: Round 1's "
            "model/floor MMD ratio was flat, so capacity was not implicated.",
            file=sys.stderr,
        )
        return 2
    required = [SCGEN_AE_STUDY, SCGEN_AE_WORKER, SCGEN_AE_SPEC]
    missing = [path for path in required if not path.exists()]
    if missing:
        print("[hub] AE follow-up is missing required files:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        return 1
    if not _ae_followup_gate_ok(round_number):
        return 2
    process = subprocess.run(
        [
            sys.executable,
            str(SCGEN_AE_STUDY),
            f"generate-round{int(round_number)}",
            "--spec",
            str(SCGEN_AE_SPEC),
            "--concurrency",
            str(int(concurrency)),
        ],
        cwd=ABLATION,
    )
    if process.returncode:
        return process.returncode
    manifest = (
        ABLATION
        / "results"
        / "stage0_ae_followup"
        / "manifests"
        / f"round{int(round_number)}_seed0.manifest"
    )
    configs = [line for line in manifest.read_text().splitlines() if line.strip()]
    print()
    print(
        f"[hub] Round {int(round_number)}: {len(configs)} fixed CPU variants "
        f"(max concurrency {int(concurrency)})."
    )
    print("[hub] Review, then submit manually:")
    print(
        "  sbatch "
        f"--array=1-{len(configs)}%{int(concurrency)} "
        f"--export=ALL,AE_MANIFEST={manifest.resolve()} "
        f"{SCGEN_AE_WORKER.resolve()}"
    )
    print("[hub] The hub did not submit anything.")
    return 0


def scgen_ae_followup_summarize(round_number: int) -> int:
    if round_number == 2:
        print("[hub] Round 2 is skipped; nothing to summarize.", file=sys.stderr)
        return 2
    process = subprocess.run(
        [
            sys.executable,
            str(SCGEN_AE_STUDY),
            f"summarize-round{int(round_number)}",
            "--spec",
            str(SCGEN_AE_SPEC),
        ],
        cwd=ABLATION,
    )
    return process.returncode
