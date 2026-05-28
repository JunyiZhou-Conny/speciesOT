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
import sys
from typing import Any

from speciesOT.hub.discover import build_catalog


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

    # Sort
    if args.sort:
        def keyfn(r):
            v = getattr(r, args.sort, None)
            if v is None:
                return (1, 0)  # sort None last
            return (0, v)

        catalog.records.sort(key=keyfn, reverse=args.desc)

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
        else:
            r2, mmd = "—", "—"

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
        ]
        print("  ".join(f"{v:<{w}}" for v, w in row))

    print()
    print(
        f"[hub] {len(catalog)} models discovered across {len(catalog.walk_roots)} root(s)."
    )
    return 0


def _show_command(args: argparse.Namespace) -> int:
    catalog = build_catalog()
    rec = catalog.by_run_id(args.run_id)
    if rec is None:
        print(f"[hub] no model with run_id={args.run_id!r}", file=sys.stderr)
        print(
            "[hub] hint: run `hub list` to see available run_ids.",
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
        print(f"    last run at       : {_format_value(ev.last_run_at)}")
        print(f"    imputed h5ad      : {_format_value(ev.imputed_h5ad_path)}")

    return 0


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

    show_p = sub.add_parser("show", help="show full detail for a single model")
    show_p.add_argument(
        "run_id",
        help="run_id, e.g. hvg_seurat_d_ood/impact_cellot",
    )
    show_p.set_defaults(func=_show_command)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
