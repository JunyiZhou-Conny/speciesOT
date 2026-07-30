"""Command-line interface for the speciesOT hub (v0).

Usage:
    python -m speciesOT.hub.cli list [--filter key=value ...] [--sort field] [--desc]
    python -m speciesOT.hub.cli show <run_id>

Examples:
    python -m speciesOT.hub.cli list
    python -m speciesOT.hub.cli list --filter family=impact_cellot
    python -m speciesOT.hub.cli list --filter hvg_method=pearson_residuals --filter status=done
    python -m speciesOT.hub.cli show hvg_seurat_d_ood/impact_cellot
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import Any

from pathlib import Path

from speciesOT.hub.discover import build_catalog
from speciesOT.hub.figures import apply_matches, match_all, summarize_matches
from speciesOT.hub.render import (
    DEFAULT_CARDS_DIR,
    export_csv,
    export_md,
    render_comparison,
    write_card,
    write_index,
)
from speciesOT.hub.vault import (
    DEFAULT_EXPERIMENTS_DIR,
    write_experiment_note,
    write_experiments_index,
)
from speciesOT.hub.spec import (
    ExperimentSpec,
    find_cell_sibling,
    generate_artifacts,
    load_spec_yaml,
    render_submission_chain,
    spec_from_record,
    write_spec_yaml,
)
from speciesOT.hub.lps import (
    icnn_generate as lps_icnn_generate,
    icnn_summarize as lps_icnn_summarize,
    scgen_ae_followup_generate as lps_scgen_ae_followup_generate,
    scgen_ae_followup_summarize as lps_scgen_ae_followup_summarize,
    scgen_paper_audit_generate as lps_scgen_paper_audit_generate,
    scgen_paper_generate as lps_scgen_paper_generate,
)


def _format_value(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "Y" if v else "N"
    if isinstance(v, float):
        # Use scientific notation for very small magnitudes (e.g. lr=0.0001).
        if v != 0 and abs(v) < 0.01:
            return f"{v:.2e}"
        return f"{v:.3f}"
    if isinstance(v, list):
        if not v:
            return "—"
        return ",".join(str(x) for x in v)
    return str(v)


def _coerce_filter_value(v: str) -> Any:
    """Heuristically coerce filter CLI strings into bools/ints where reasonable."""
    if v.lower() in {"true", "yes", "y"}:
        return True
    if v.lower() in {"false", "no", "n"}:
        return False
    if v.lstrip("-").isdigit():
        return int(v)
    return v


def _list_command(args: argparse.Namespace) -> int:
    catalog = build_catalog()

    # Apply filters
    if args.filter:
        filters = {}
        for spec in args.filter:
            if "=" not in spec:
                print(f"[hub] ignoring malformed filter: {spec!r}", file=sys.stderr)
                continue
            k, raw_v = spec.split("=", 1)
            filters[k] = _coerce_filter_value(raw_v)
        catalog = catalog.filter(**filters)

    # Sort. Always secondary-sort by run_id for stable output within each group.
    if args.sort:
        def keyfn(r):
            v = getattr(r, args.sort, None)
            # (is_none_flag, primary_value, run_id). is_none_flag pushes None values to the end.
            if v is None:
                return (1, "", r.run_id)
            # Coerce non-comparable types to string so e.g. mixed-type fields don't blow up.
            return (0, v if isinstance(v, (str, int, float, bool)) else str(v), r.run_id)

        catalog.records.sort(key=keyfn, reverse=args.desc)
    else:
        # Default order: stable alphabetical by run_id.
        catalog.records.sort(key=lambda r: r.run_id)

    if not catalog.records:
        print("[hub] no models found.")
        return 0

    # Layout: fixed-width columns. run_id is wide because experiment names are long.
    cols = [
        ("run_id", 50),
        ("family", 18),
        ("hvg_method", 18),
        ("status", 14),
        ("holdout", 28),
        ("R^2", 6),
        ("MMD", 7),
        ("fgc_dec", 8),
    ]

    header = "  ".join(f"{name:<{w}}" for name, w in cols)
    print(header)
    print("-" * len(header))

    for rec in catalog.records:
        if rec.holdout_cell_types:
            holdout = ",".join(rec.holdout_cell_types)
        elif rec.holdout_species:
            holdout = f"species={rec.holdout_species}"
        else:
            holdout = "—"

        # Headline metrics: prefer data_space eval, then latent_space, then any
        eval_for_headline = None
        if rec.evals:
            ds = [e for e in rec.evals if e.space == "data_space"]
            ls = [e for e in rec.evals if e.space == "latent_space"]
            eval_for_headline = (ds + ls + rec.evals)[0]
        if eval_for_headline:
            r2 = _format_value(eval_for_headline.headline_r2_means)
            mmd = _format_value(eval_for_headline.headline_mmd)
            fgc_dec = _format_value(eval_for_headline.frac_gap_closed_decoded)
        else:
            r2, mmd, fgc_dec = "—", "—", "—"

        def _trunc(s: str, w: int) -> str:
            return (s[: w - 2] + "..") if len(s) > w else s

        row = [
            (_trunc(rec.run_id, 50), 50),
            (_trunc(rec.family, 18), 18),
            (_trunc(rec.hvg_method or "—", 18), 18),
            (_trunc(rec.status, 14), 14),
            (_trunc(holdout, 28), 28),
            (r2, 6),
            (mmd, 7),
            (fgc_dec, 8),
        ]
        print("  ".join(f"{v:<{w}}" for v, w in row))

    print()
    print(
        f"[hub] {len(catalog)} models discovered across {len(catalog.walk_roots)} root(s)."
    )
    return 0


def _scorecard_command(args: argparse.Namespace) -> int:
    """The single repo-wide leaderboard, sorted by the NORTH-STAR metric
    (frac_gap_closed_decoded, AE-honest). Replaces eyeballing notebook 22 for the
    headline ranking; notebook 22 stays for the deep-dive / figures.

    By default shows only runs whose decoded sidecar has been computed
    (`./hub metrics <run_id>`); pass --all to include every run with a data_space
    eval (decoded column shows "—" where not yet computed).
    """
    catalog = build_catalog()

    def headline_eval(rec):
        ds = [e for e in rec.evals if e.space == "data_space"]
        if not ds:
            return None
        # Prefer an eval that actually has the decoded north-star computed.
        with_dec = [e for e in ds if e.frac_gap_closed_decoded is not None]
        return (with_dec or ds)[0]

    rows = []
    for rec in catalog.records:
        ev = headline_eval(rec)
        if ev is None:
            continue
        if not args.all and ev.frac_gap_closed_decoded is None:
            continue
        if args.family and rec.family != args.family:
            continue
        rows.append((rec, ev))

    # Sort by decoded frac_gap_closed desc; runs without it sink to the bottom.
    rows.sort(
        key=lambda re: (
            re[1].frac_gap_closed_decoded if re[1].frac_gap_closed_decoded is not None else -1e9
        ),
        reverse=True,
    )

    if not rows:
        print("[hub] no runs with a decoded scorecard yet. Run `./hub metrics <run_id>` "
              "on a data_space eval, or pass --all to see raw-only runs.")
        return 0

    cols = [
        ("run_id", 48),
        ("family", 14),
        ("mode", 5),
        ("fgc_dec", 8),
        ("fr2_dec", 8),
        ("mean_js", 8),
        ("fgc_raw", 8),
        ("R^2", 6),
        ("status", 12),
    ]
    lines = []
    header = "  ".join(f"{name:<{w}}" for name, w in cols)
    lines.append(header)
    lines.append("-" * len(header))

    def _trunc(s: str, w: int) -> str:
        return (s[: w - 2] + "..") if len(s) > w else s

    def _f(v):
        return f"{v:.3f}" if isinstance(v, float) else "—"

    for rec, ev in rows:
        if rec.train_includes_holdout is True:
            mode = "iid"
        elif rec.train_includes_holdout is False:
            mode = "ood"
        else:
            mode = "—"
        row = [
            (_trunc(rec.run_id, 48), 48),
            (_trunc(rec.family, 14), 14),
            (mode, 5),
            (_f(ev.frac_gap_closed_decoded), 8),
            (_f(ev.frac_r2_closed_decoded), 8),
            (_f(ev.headline_js), 8),
            (_f(ev.frac_gap_closed), 8),
            (_f(ev.headline_r2_means), 6),
            (_trunc(rec.status, 12), 12),
        ]
        lines.append("  ".join(f"{v:<{w}}" for v, w in row))

    text = "\n".join(lines)
    if args.out:
        Path(args.out).write_text(text + "\n")
        print(f"[hub] wrote scorecard to {args.out}")
    else:
        print(text)
        print()
        print("[hub] north-star = fgc_dec (frac_gap_closed_decoded, AE-honest). "
              "fgc_raw is the raw-frame value (unreliable for IMPACT). "
              "Run `./hub metrics <run_id>` to populate missing rows.")
    return 0


def _show_command(args: argparse.Namespace) -> int:
    catalog = build_catalog()
    try:
        rec = catalog.by_run_id(args.run_id)
    except ValueError as e:
        print(f"[hub] {e}", file=sys.stderr)
        return 2
    if rec is None:
        print(f"[hub] no model with run_id={args.run_id!r}", file=sys.stderr)
        print(
            "[hub] hint: run `./hub list` to see available run_ids.",
            file=sys.stderr,
        )
        return 1

    print(f"run_id                : {rec.run_id}")
    print(f"model_dir             : {rec.model_dir}")
    print(f"family                : {rec.family}  (alias seen: {rec.family_alias_seen})")
    print(f"status                : {rec.status}")
    print()
    print("--- Data provenance ---")
    print(f"data_source           : {_format_value(rec.data_source)}")
    print(f"data_file             : {_format_value(rec.data_file)}")
    print(f"normalization         : {_format_value(rec.normalization)}")
    print(f"log1p_applied         : {_format_value(rec.log1p_applied)}")
    print(f"hvg_method            : {_format_value(rec.hvg_method)}")
    print(f"hvg_input_layer       : {_format_value(rec.hvg_input_layer)}")
    print(f"hvg_batch_key         : {_format_value(rec.hvg_batch_key)}")
    print()
    print("--- Framing ---")
    print(f"framing               : {_format_value(rec.framing)}")
    print(f"condition (column)    : {_format_value(rec.condition)}")
    print(f"source                : {_format_value(rec.source)}")
    print(f"target                : {_format_value(rec.target)}")
    print(f"transport_direction   : {_format_value(rec.transport_direction)}")
    print()
    print("--- Holdout ---")
    print(f"cell_types            : {_format_value(rec.holdout_cell_types)}")
    print(f"species               : {_format_value(rec.holdout_species)}")
    print(f"train_includes_holdout: {_format_value(rec.train_includes_holdout)}")
    print(f"datasplit_strategy    : {_format_value(rec.datasplit_strategy)}")
    print()
    print("--- Architecture ---")
    print(f"model_name (lib)      : {_format_value(rec.model_name)}")
    print(f"hidden_units          : {_format_value(rec.hidden_units)}")
    print(f"latent_dim            : {_format_value(rec.latent_dim)}")
    print(f"n_iters               : {_format_value(rec.n_iters)}")
    print(f"n_inner_iters         : {_format_value(rec.n_inner_iters)}")
    print(f"batch_size            : {_format_value(rec.batch_size)}")
    print(f"lr                    : {_format_value(rec.lr)}")
    print(f"optimizer             : {_format_value(rec.optimizer)}")
    print(f"ae_emb_path           : {_format_value(rec.ae_emb_path)}")
    print()
    print("--- Lineage ---")
    print(f"generated_by          : {_format_value(rec.generated_by)}")
    print(f"created_at            : {_format_value(rec.created_at)}")
    print(f"last_modified         : {_format_value(rec.last_modified)}")
    print()
    print(f"--- Evaluations ({len(rec.evals)}) ---")
    if not rec.evals:
        print("  (none)")
    for ev in rec.evals:
        print(f"  {ev.eval_id}")
        print(f"    space             : {_format_value(ev.space)}")
        print(f"    setting           : {_format_value(ev.setting)}")
        print(f"    n_cells present   : {_format_value(ev.n_cells_present)}")
        print(f"    R^2 of means      : {_format_value(ev.headline_r2_means)}")
        print(f"    MMD               : {_format_value(ev.headline_mmd)}")
        if ev.frac_gap_closed_decoded is not None or ev.frac_r2_closed_decoded is not None:
            print(f"    frac_gap_closed (decoded, NORTH-STAR) : {_format_value(ev.frac_gap_closed_decoded)}")
            print(f"    frac_r2_closed (decoded, guardrail)   : {_format_value(ev.frac_r2_closed_decoded)}")
            print(f"    MMD ae-recon floor / decoded ceiling  : {_format_value(ev.mmd_ae_recon_floor)} / {_format_value(ev.mmd_decoded_ceiling)}")
        if ev.headline_mmd_floor is not None or ev.headline_mmd_ceiling is not None:
            print(f"    MMD floor/ceiling (raw frame)         : {_format_value(ev.headline_mmd_floor)} / {_format_value(ev.headline_mmd_ceiling)}")
            print(f"    frac_gap_closed (raw, unreliable)     : {_format_value(ev.frac_gap_closed)}")
        if ev.headline_js is not None:
            print(f"    mean per-gene JS (KL-style)           : {_format_value(ev.headline_js)}")
        print(f"    last run at       : {_format_value(ev.last_run_at)}")
        print(f"    imputed h5ad      : {_format_value(ev.imputed_h5ad_path)}")

    return 0


def _card_command(args: argparse.Namespace) -> int:
    catalog = build_catalog()

    if args.all:
        if args.run_id:
            print(
                "[hub] --all is mutually exclusive with a run_id argument",
                file=sys.stderr,
            )
            return 2
        out_dir = args.out_dir or DEFAULT_CARDS_DIR
        n_cards = 0
        for rec in catalog.records:
            try:
                write_card(rec, out_dir)
                n_cards += 1
            except OSError as e:
                print(f"[hub] could not write card for {rec.run_id}: {e}", file=sys.stderr)
        index_path = write_index(catalog.records, out_dir)
        print(f"[hub] wrote {n_cards} cards + INDEX.md to {out_dir}")
        print(f"[hub] open the index: {index_path}")
        return 0

    if not args.run_id:
        print("[hub] specify a run_id, or pass --all", file=sys.stderr)
        return 2

    try:
        rec = catalog.by_run_id(args.run_id)
    except ValueError as e:
        print(f"[hub] {e}", file=sys.stderr)
        return 2
    if rec is None:
        print(f"[hub] no model with run_id={args.run_id!r}", file=sys.stderr)
        return 1
    out_path = write_card(rec, args.out_dir)
    print(f"[hub] wrote card: {out_path}")
    return 0


def _vault_command(args: argparse.Namespace) -> int:
    """Generate Obsidian-ready experiment notes (frontmatter + tags + wikilinks).

    Unlike `./hub card` (rich, HPC-only, gitignored), these notes are tracked
    and meant to sync to a local Obsidian vault. See docs/obsidian_setup.md.
    """
    catalog = build_catalog()
    out_dir = args.out_dir or DEFAULT_EXPERIMENTS_DIR
    all_ids = {r.run_id for r in catalog.records}
    n = 0
    for rec in catalog.records:
        try:
            write_experiment_note(rec, all_ids, out_dir)
            n += 1
        except OSError as e:
            print(f"[hub] could not write vault note for {rec.run_id}: {e}", file=sys.stderr)
    index_path = write_experiments_index(catalog.records, out_dir)
    print(f"[hub] wrote {n} experiment notes + {index_path.name} to {out_dir}")
    print("[hub] open docs/ as an Obsidian vault (see docs/obsidian_setup.md) to see the graph.")
    return 0


from speciesOT.hub.paths import (  # noqa: E402
    CELLOT_DIR,
    WORKSPACE_ROOT,
    env_python_candidates,
)


# The data-prep stage needs scanpy >= 1.12 (Pearson residuals, seurat_v3_paper),
# which lives in the `analysis` env — not the CellOT env the hub runs in. So
# `./hub prep` shells out to the analysis interpreter running
# `python -m speciesOT.hub.prep`. Override the interpreter with SPECIESOT_ANALYSIS_PY.
_ANALYSIS_PY_CANDIDATES = env_python_candidates("analysis", "SPECIESOT_ANALYSIS_PY")


def _resolve_analysis_py() -> str | None:
    for cand in _ANALYSIS_PY_CANDIDATES:
        if cand and Path(cand).exists():
            return cand
    return None


def _prep_command(args: argparse.Namespace) -> int:
    """Materialize the training .h5ad from a spec (v2).

    Delegates to `python -m speciesOT.hub.prep` under the `analysis` conda env,
    since the HVG flavors require scanpy >= 1.12 (not in the CellOT env). See
    docs/hub_design.md §14 and docs/hub_handoff.md §4.
    """
    spec_path = args.spec
    if not spec_path.exists():
        print(f"[hub] spec not found: {spec_path}", file=sys.stderr)
        return 2

    analysis_py = _resolve_analysis_py()
    if analysis_py is None:
        print(
            "[hub] could not locate the `analysis` env python (scanpy >= 1.12).\n"
            "[hub] set SPECIESOT_ANALYSIS_PY to its interpreter, or activate the env and run:\n"
            f"[hub]   python -m speciesOT.hub.prep {spec_path}",
            file=sys.stderr,
        )
        return 2

    cmd = [analysis_py, "-m", "speciesOT.hub.prep", str(spec_path.resolve())]
    if args.force:
        cmd.append("--force")
    if args.keep_intermediate:
        cmd.append("--keep-intermediate")

    print(f"[hub] prep via analysis env: {analysis_py}")
    print(f"[hub] $ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(WORKSPACE_ROOT))
    return proc.returncode


def _metrics_command(args: argparse.Namespace) -> int:
    """Compute extended metrics (MMD floor/ceiling, fraction-of-gap-closed, mean JS)
    for a model's data-space eval(s) and write an `extended_metrics.csv` sidecar.

    Shells out to `scripts/extended_metrics.py` using the current (CellOT-env)
    interpreter; the hub catalog then surfaces the metrics in `show`/`card`/`compare`.
    """
    catalog = build_catalog()
    try:
        rec = catalog.by_run_id(args.run_id)
    except ValueError as e:
        print(f"[hub] {e}", file=sys.stderr)
        return 2
    if rec is None:
        print(f"[hub] no model with run_id={args.run_id!r}", file=sys.stderr)
        return 1

    data_space_evals = [ev for ev in rec.evals if ev.space == "data_space"]
    if not data_space_evals:
        print(f"[hub] {rec.run_id} has no data_space eval to compute metrics on",
              file=sys.stderr)
        return 1

    # Two sidecars are written per eval:
    #   extended_metrics.py     -> extended_metrics.csv      (raw-frame + JS)
    #   decoded_frame_metrics.py -> decoded_frame_metrics.csv (AE-honest north-star)
    # The decoded frame is the headline for IMPACT_CellOT (see §5.9); run both so
    # the catalog can surface frac_gap_closed_decoded everywhere.
    scripts = [
        CELLOT_DIR / "scripts" / "extended_metrics.py",
        CELLOT_DIR / "scripts" / "decoded_frame_metrics.py",
    ]
    env = dict(os.environ, PYTHONPATH=str(CELLOT_DIR))
    rc = 0
    for ev in data_space_evals:
        for script in scripts:
            cmd = [
                sys.executable, str(script),
                "--outdir", str(rec.model_dir),
                "--setting", ev.setting or "ood",
                "--where", "data_space",
                "--embedding", "ae",
                "--evalprefix", ev.eval_id,
            ]
            if args.n_cells:
                cmd += ["--n_cells", args.n_cells]
            print(f"[hub] metrics ({script.name}) for {rec.run_id} [{ev.eval_id}]")
            print(f"[hub] $ {' '.join(cmd)}")
            proc = subprocess.run(cmd, cwd=str(CELLOT_DIR), env=env)
            rc = rc or proc.returncode
    return rc


def _handoff_command(args: argparse.Namespace) -> int:
    """Emit a handoff manifest bundling the three boundary artifacts for the
    downstream (mentor) track: processed dataset, preprocessing description, and
    model spec. Markdown + JSON.
    """
    from dataclasses import asdict

    catalog = build_catalog()
    try:
        rec = catalog.by_run_id(args.run_id)
    except ValueError as e:
        print(f"[hub] {e}", file=sys.stderr)
        return 2
    if rec is None:
        print(f"[hub] no model with run_id={args.run_id!r}", file=sys.stderr)
        return 1

    sibling = find_cell_sibling(rec, catalog.records)
    spec = spec_from_record(rec, sibling=sibling)
    spec_d = asdict(spec)

    # 1. Processed dataset pointer (+ size if resolvable under cellot_gpu).
    data_file = rec.data_file or spec.data_file or ""
    data_path = (CELLOT_DIR / data_file) if data_file else None
    data_exists = bool(data_path and data_path.exists())
    data_bytes = data_path.stat().st_size if data_exists else None

    # 2. Preprocessing description (the spec's intent fields).
    prep_keys = [
        "source_datasets", "assay_filter", "cap_cells_per_type", "ortholog_source",
        "hvg_method", "hvg_n_top", "hvg_input_layer", "hvg_batch_key", "log1p_applied",
        "holdout_cell_types", "holdout_species", "datasplit_strategy", "mode",
        "test_size", "random_state",
    ]
    prep = {k: spec_d.get(k) for k in prep_keys}

    # 3. Model spec (architecture + hyperparameters).
    model_spec = {
        "family": rec.family,
        "model_name": rec.model_name,
        "hidden_units": rec.hidden_units,
        "latent_dim": rec.latent_dim,
        "lr": rec.lr,
        "batch_size": rec.batch_size,
        "n_iters": rec.n_iters,
        "n_inner_iters": rec.n_inner_iters,
        "optimizer": rec.optimizer,
        "ae_emb_path": rec.ae_emb_path,
    }

    # 4. Headline metrics for context.
    evals_summary = []
    for ev in rec.evals:
        evals_summary.append({
            "eval_id": ev.eval_id,
            "r2_means": ev.headline_r2_means,
            "mmd": ev.headline_mmd,
            "frac_gap_closed_decoded": ev.frac_gap_closed_decoded,
            "frac_r2_closed_decoded": ev.frac_r2_closed_decoded,
            "mmd_ae_recon_floor": ev.mmd_ae_recon_floor,
            "mmd_decoded_ceiling": ev.mmd_decoded_ceiling,
            "mmd_floor_raw": ev.headline_mmd_floor,
            "mmd_ceiling_raw": ev.headline_mmd_ceiling,
            "frac_gap_closed_raw": ev.frac_gap_closed,
            "mean_js": ev.headline_js,
        })

    manifest = {
        "run_id": rec.run_id,
        "generated_at": catalog.discovered_at.isoformat(),
        "processed_dataset": {
            "data_file": data_file,
            "exists": data_exists,
            "bytes": data_bytes,
        },
        "preprocessing": prep,
        "model_spec": model_spec,
        "evaluations": evals_summary,
    }

    out_dir = args.out_dir or (WORKSPACE_ROOT / "handoff")
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = rec.run_id.replace("/", "__")
    json_path = out_dir / f"{stem}.handoff.json"
    md_path = out_dir / f"{stem}.handoff.md"

    import json as _json
    json_path.write_text(_json.dumps(manifest, indent=2, default=str))

    def _fmt(v):
        return "—" if v is None else v

    def _fmtr(v):
        return "—" if v is None else (f"{v:.4f}" if isinstance(v, float) else v)

    lines = [
        f"# Handoff manifest — `{rec.run_id}`", "",
        f"Generated {manifest['generated_at']}. The in-vitro (atlas) top-track "
        "deliverable for the downstream (BCG / batch-correction / prediction) track.",
        "",
        "## 1. Processed dataset", "",
        "| Field | Value |", "|---|---|",
        f"| data_file | `{_fmt(data_file)}` |",
        f"| exists | {data_exists} |",
        f"| size (bytes) | {_fmt(data_bytes)} |",
        "",
        "## 2. Preprocessing description", "",
        "| Field | Value |", "|---|---|",
    ]
    for k in prep_keys:
        lines.append(f"| {k} | `{_fmt(prep.get(k))}` |")
    lines += ["", "## 3. Model spec", "", "| Field | Value |", "|---|---|"]
    for k, v in model_spec.items():
        lines.append(f"| {k} | `{_fmt(v)}` |")
    lines += ["", "## 4. Evaluations", ""]
    if evals_summary:
        lines += [
            "| eval | R² | MMD | floor | ceiling | frac closed | mean JS |",
            "|---|---|---|---|---|---|---|",
        ]
        for e in evals_summary:
            lines.append(
                f"| `{e['eval_id']}` | {_fmtr(e['r2_means'])} | {_fmtr(e['mmd'])} | "
                f"{_fmtr(e['mmd_floor'])} | {_fmtr(e['mmd_ceiling'])} | "
                f"{_fmtr(e['frac_gap_closed'])} | {_fmtr(e['mean_js'])} |"
            )
    else:
        lines.append("_(no evaluations found)_")
    lines.append("")
    md_path.write_text("\n".join(lines))

    print(f"[hub] wrote handoff manifest:\n  {md_path}\n  {json_path}")
    return 0


def _spec_dump_command(args: argparse.Namespace) -> int:
    catalog = build_catalog()
    try:
        rec = catalog.by_run_id(args.run_id)
    except ValueError as e:
        print(f"[hub] {e}", file=sys.stderr)
        return 2
    if rec is None:
        print(f"[hub] no model with run_id={args.run_id!r}", file=sys.stderr)
        return 1
    # If a sibling (scgen↔impact_cellot) exists in the same experiment dir, use its
    # actual hyperparameters for the sibling slot. Makes the dump→generate round-trip
    # lossless instead of defaulting the sibling.
    sibling = find_cell_sibling(rec, catalog.records)
    spec = spec_from_record(rec, sibling=sibling)
    if sibling is not None:
        print(f"[hub] including sibling {sibling.family} from {sibling.run_id} for round-trip fidelity", file=sys.stderr)
    if args.out:
        write_spec_yaml(spec, args.out)
        print(f"[hub] wrote spec: {args.out}")
    else:
        import yaml as _yaml
        from dataclasses import asdict
        print(_yaml.safe_dump(asdict(spec), default_flow_style=False, sort_keys=False))
    return 0


def _generate_command(args: argparse.Namespace) -> int:
    spec = load_spec_yaml(args.spec)
    plan = generate_artifacts(spec, dry_run=args.dry_run, force=args.force)

    verb = "would write" if args.dry_run else "wrote"
    print(f"[hub] generate spec={args.spec.name} tag={spec.experiment_tag}")
    print(f"[hub] {verb} {len(plan.written)} files:")
    for p in plan.written:
        try:
            rel = p.relative_to(WORKSPACE_ROOT)
        except ValueError:
            rel = p
        print(f"    {rel}")
    for link, target in plan.symlinks:
        try:
            rel = link.relative_to(WORKSPACE_ROOT)
        except ValueError:
            rel = link
        print(f"    {rel} -> {target}  (symlink)")
    if plan.skipped:
        print(f"[hub] skipped {len(plan.skipped)} (use --force to overwrite):")
        for p, reason in plan.skipped:
            try:
                rel = p.relative_to(WORKSPACE_ROOT)
            except ValueError:
                rel = p
            print(f"    {rel}  ({reason})")

    if not args.dry_run:
        print()
        print(render_submission_chain(spec))
    return 0


def _lps_icnn_generate_command(args: argparse.Namespace) -> int:
    return lps_icnn_generate(args.round, concurrency=args.concurrency)


def _lps_icnn_summarize_command(args: argparse.Namespace) -> int:
    return lps_icnn_summarize(args.round)


def _lps_scgen_paper_generate_command(args: argparse.Namespace) -> int:
    return lps_scgen_paper_generate()


def _lps_scgen_paper_audit_generate_command(args: argparse.Namespace) -> int:
    return lps_scgen_paper_audit_generate()


def _lps_scgen_ae_followup_generate_command(args: argparse.Namespace) -> int:
    return lps_scgen_ae_followup_generate(
        args.round, concurrency=args.concurrency
    )


def _lps_scgen_ae_followup_summarize_command(args: argparse.Namespace) -> int:
    return lps_scgen_ae_followup_summarize(args.round)


def _export_command(args: argparse.Namespace) -> int:
    catalog = build_catalog()
    fmt = args.format
    if fmt == "csv":
        out = args.out or (WORKSPACE_ROOT / "experiments_inventory.csv")
        export_csv(catalog.records, out)
        print(f"[hub] wrote {len(catalog)} rows to {out}")
    elif fmt == "md":
        out = args.out or (WORKSPACE_ROOT / "experiments_inventory.md")
        export_md(catalog.records, out)
        print(f"[hub] wrote markdown summary to {out}")
    else:
        print(f"[hub] unknown format: {fmt!r} (use csv or md)", file=sys.stderr)
        return 2
    return 0


def _compare_command(args: argparse.Namespace) -> int:
    catalog = build_catalog()

    def _resolve(rid: str):
        try:
            return catalog.by_run_id(rid)
        except ValueError as e:
            print(f"[hub] {e}", file=sys.stderr)
            return None

    rec_a = _resolve(args.run_id_a)
    rec_b = _resolve(args.run_id_b)
    if rec_a is None or rec_b is None:
        if rec_a is None:
            print(f"[hub] no model with run_id={args.run_id_a!r}", file=sys.stderr)
        if rec_b is None:
            print(f"[hub] no model with run_id={args.run_id_b!r}", file=sys.stderr)
        return 1

    md = render_comparison(rec_a, rec_b)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md)
        print(f"[hub] wrote comparison: {args.out}")
    else:
        print(md)
    return 0


def _attach_figures_command(args: argparse.Namespace) -> int:
    catalog = build_catalog()
    matches = match_all(catalog)

    if args.dry_run:
        print(summarize_matches(matches))
        print()
        print(f"[hub] dry-run: would create {len(matches)} symlinks. Re-run without --dry-run to apply.")
        return 0

    if args.summary:
        print(summarize_matches(matches))
        print()

    stats = apply_matches(matches, overwrite=args.overwrite)
    print(
        f"[hub] attach-figures: created {stats['created']} symlinks, "
        f"skipped {stats['skipped_existing']} existing, "
        f"errors {stats['errors']}."
    )
    if not args.overwrite and stats["skipped_existing"] > 0:
        print(
            "[hub] hint: pass --overwrite to replace existing symlinks (e.g. after a figure update)."
        )
    return 0 if stats["errors"] == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="hub",
        description="speciesOT model-card hub (v0).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    list_p = sub.add_parser("list", help="list models in the catalog")
    list_p.add_argument(
        "--filter",
        action="append",
        help="key=value filter (repeatable). e.g. --filter family=impact_cellot",
    )
    list_p.add_argument("--sort", help="field name to sort by")
    list_p.add_argument("--desc", action="store_true", help="sort descending")
    list_p.set_defaults(func=_list_command)

    scorecard_p = sub.add_parser(
        "scorecard",
        help="the single leaderboard: all runs ranked by the north-star "
        "(frac_gap_closed_decoded). The headline answer to 'are we improving?'",
    )
    scorecard_p.add_argument(
        "--all", action="store_true",
        help="include runs whose decoded metric isn't computed yet (default: only scored runs)",
    )
    scorecard_p.add_argument(
        "--family", help="restrict to one family, e.g. --family impact_cellot",
    )
    scorecard_p.add_argument(
        "--out", help="write the table to a file instead of stdout",
    )
    scorecard_p.set_defaults(func=_scorecard_command)

    show_p = sub.add_parser("show", help="show full detail for a single model")
    show_p.add_argument(
        "run_id",
        help="run_id, e.g. hvg_seurat_d_ood/impact_cellot",
    )
    show_p.set_defaults(func=_show_command)

    card_p = sub.add_parser(
        "card",
        help="render a markdown model card (openable in Cursor preview)",
    )
    card_p.add_argument(
        "run_id",
        nargs="?",
        help="run_id to render; omit and pass --all to render every model",
    )
    card_p.add_argument(
        "--all",
        action="store_true",
        help="render a card for every model + an INDEX.md grouping by family",
    )
    card_p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help=f"output directory (default: {DEFAULT_CARDS_DIR})",
    )
    card_p.set_defaults(func=_card_command)

    vault_p = sub.add_parser(
        "vault",
        help="generate Obsidian-ready experiment notes (frontmatter + tags + wikilinks) into docs/experiments/",
    )
    vault_p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help=f"output directory (default: {DEFAULT_EXPERIMENTS_DIR})",
    )
    vault_p.set_defaults(func=_vault_command)

    attach_p = sub.add_parser(
        "attach-figures",
        help=(
            "scan speciesOT/baseline/analysis/*_outputs/ and symlink matching figures "
            "into <model_dir>/figures/ so they appear on the model cards"
        ),
    )
    attach_p.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be linked without creating symlinks",
    )
    attach_p.add_argument(
        "--summary",
        action="store_true",
        help="print the per-model match summary before applying",
    )
    attach_p.add_argument(
        "--overwrite",
        action="store_true",
        help="overwrite existing symlinks (default: skip if target exists)",
    )
    attach_p.set_defaults(func=_attach_figures_command)

    compare_p = sub.add_parser(
        "compare",
        help="side-by-side comparison of two model cards (spec deltas + metric deltas)",
    )
    compare_p.add_argument("run_id_a", help="first run_id")
    compare_p.add_argument("run_id_b", help="second run_id")
    compare_p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write the comparison markdown to this path (default: print to stdout)",
    )
    compare_p.set_defaults(func=_compare_command)

    export_p = sub.add_parser(
        "export",
        help="export the full catalog to csv or md (replaces experiments_inventory.csv/.md)",
    )
    export_p.add_argument("format", choices=["csv", "md"], help="output format")
    export_p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output path (default: experiments_inventory.{csv,md} at workspace root)",
    )
    export_p.set_defaults(func=_export_command)

    spec_p = sub.add_parser(
        "spec",
        help="dump an existing model's spec as YAML (v1; spec system in progress)",
    )
    spec_sub = spec_p.add_subparsers(dest="spec_cmd", required=True)
    spec_dump_p = spec_sub.add_parser(
        "dump", help="dump a model's reverse-engineered spec to YAML"
    )
    spec_dump_p.add_argument("run_id", help="run_id of the model to dump from")
    spec_dump_p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output YAML path (default: print to stdout)",
    )
    spec_dump_p.set_defaults(func=_spec_dump_command)

    generate_p = sub.add_parser(
        "generate",
        help="materialize configs + sbatches from a spec YAML",
    )
    generate_p.add_argument("spec", type=Path, help="path to a spec YAML")
    generate_p.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be written without creating files",
    )
    generate_p.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing configs and sbatches (default: skip)",
    )
    generate_p.set_defaults(func=_generate_command)

    prep_p = sub.add_parser(
        "prep",
        help="materialize the .h5ad data file from a spec (v2; runs in the analysis env)",
    )
    prep_p.add_argument("spec", type=Path, help="path to a spec YAML")
    prep_p.add_argument(
        "--force",
        action="store_true",
        help="overwrite the output .h5ad if it already exists (default: refuse)",
    )
    prep_p.add_argument(
        "--keep-intermediate",
        action="store_true",
        help="keep the pre-round-trip anndata-1.x temp file (for debugging)",
    )
    prep_p.set_defaults(func=_prep_command)

    metrics_p = sub.add_parser(
        "metrics",
        help="compute extended metrics (MMD floor/ceiling, fraction closed, mean JS) "
        "for a model's data-space eval(s); writes an extended_metrics.csv sidecar",
    )
    metrics_p.add_argument("run_id", help="run_id (exact or unique suffix)")
    metrics_p.add_argument(
        "--n_cells", default=None,
        help="comma-separated subsample sizes (default: the script's 30,50,80)",
    )
    metrics_p.set_defaults(func=_metrics_command)

    lps_p = sub.add_parser(
        "lps",
        help="cross-species LPS studies: paper scGen replication and frozen-AE ICNN-OT",
    )
    lps_sub = lps_p.add_subparsers(dest="lps_cmd", required=True)

    lps_icnn_gen = lps_sub.add_parser(
        "icnn-generate",
        help="generate one ICNN-OT round and print its manual Slurm submission command",
    )
    lps_icnn_gen.add_argument("--round", type=int, choices=(1, 2, 3), required=True)
    lps_icnn_gen.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="maximum simultaneous Slurm array tasks (default: 4)",
    )
    lps_icnn_gen.set_defaults(func=_lps_icnn_generate_command)

    lps_icnn_summary = lps_sub.add_parser(
        "icnn-summarize",
        help="merge one ICNN-OT round's per-run metrics into its study CSV",
    )
    lps_icnn_summary.add_argument("--round", type=int, choices=(1, 2, 3), required=True)
    lps_icnn_summary.set_defaults(func=_lps_icnn_summarize_command)

    lps_scgen = lps_sub.add_parser(
        "scgen-paper-generate",
        help="validate the completed TensorFlow Fig. 5 checkpoint and print eval sbatch",
    )
    lps_scgen.set_defaults(func=_lps_scgen_paper_generate_command)

    lps_scgen_audit = lps_sub.add_parser(
        "scgen-paper-audit-generate",
        help=(
            "validate the TensorFlow Fig. 5 checkpoint and print the no-retraining "
            "Stage-0 identity audit sbatch"
        ),
    )
    lps_scgen_audit.set_defaults(func=_lps_scgen_paper_audit_generate_command)

    lps_scgen_ae = lps_sub.add_parser(
        "scgen-ae-followup-generate",
        help="generate the bounded scGen AE identity follow-up and print its sbatch",
    )
    lps_scgen_ae.add_argument("--round", type=int, choices=(1, 2, 3), required=True)
    lps_scgen_ae.add_argument("--concurrency", type=int, default=2)
    lps_scgen_ae.set_defaults(func=_lps_scgen_ae_followup_generate_command)

    lps_scgen_ae_summary = lps_sub.add_parser(
        "scgen-ae-followup-summarize",
        help="summarize a completed bounded scGen AE follow-up round",
    )
    lps_scgen_ae_summary.add_argument(
        "--round", type=int, choices=(1, 2, 3), required=True
    )
    lps_scgen_ae_summary.set_defaults(
        func=_lps_scgen_ae_followup_summarize_command
    )

    handoff_p = sub.add_parser(
        "handoff",
        help="emit a handoff manifest (dataset + preprocessing + model spec) for the "
        "downstream track",
    )
    handoff_p.add_argument("run_id", help="run_id (exact or unique suffix)")
    handoff_p.add_argument(
        "--out-dir", type=Path, default=None,
        help="directory to write the manifest into (default: <workspace>/handoff)",
    )
    handoff_p.set_defaults(func=_handoff_command)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
