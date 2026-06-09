"""Render ModelRecord instances as markdown model cards.

Cards are designed to open in Cursor's preview pane (or any markdown viewer)
with images inlined. v0.1 leaves the "diagnostic figures" section as a
placeholder — v0.5 will populate it via the figure-attachment matcher.

Default output dir: docs/model_cards/. One card per model. Filenames
substitute "/" → "__" in the run_id so paths are flat.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from speciesOT.hub.catalog import EvalRecord, ModelRecord
from speciesOT.hub.figures import list_attached_figures


# Where cards go by default.
DEFAULT_CARDS_DIR = Path(
    "/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/docs/model_cards"
)


def run_id_to_filename(run_id: str) -> str:
    """Convert a run_id like 'hvg_seurat_d_ood/impact_cellot' to a flat filename."""
    return run_id.replace("/", "__") + ".md"


def _fmt(v) -> str:
    """Markdown-safe value formatting for the table cells."""
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "Yes" if v else "No"
    if isinstance(v, float):
        if v != 0 and abs(v) < 0.01:
            return f"`{v:.2e}`"
        return f"`{v:.4f}`"
    if isinstance(v, list):
        if not v:
            return "—"
        return ", ".join(f"`{x}`" for x in v)
    if isinstance(v, Path):
        return f"`{v}`"
    return f"`{v}`"


def _eval_section(ev: EvalRecord) -> str:
    """Render one EvalRecord as a markdown subsection."""
    lines = [f"### `{ev.eval_id}`", ""]
    lines += [
        "| Field | Value |",
        "|---|---|",
        f"| space | {_fmt(ev.space)} |",
        f"| setting | {_fmt(ev.setting)} |",
        f"| n_cells present | {_fmt(ev.n_cells_present)} |",
        f"| R² (means) | {_fmt(ev.headline_r2_means)} |",
        f"| MMD | {_fmt(ev.headline_mmd)} |",
    ]
    # Extended metrics (only when the extended_metrics.csv sidecar exists)
    if ev.headline_mmd_floor is not None or ev.headline_mmd_ceiling is not None:
        lines += [
            f"| MMD floor (best achievable) | {_fmt(ev.headline_mmd_floor)} |",
            f"| MMD ceiling (identity gap) | {_fmt(ev.headline_mmd_ceiling)} |",
            f"| fraction of gap closed | {_fmt(ev.frac_gap_closed)} |",
        ]
    if ev.headline_js is not None:
        lines.append(f"| mean per-gene JS | {_fmt(ev.headline_js)} |")
    lines += [
        f"| last run at | {_fmt(ev.last_run_at)} |",
        f"| imputed.h5ad | {_fmt(ev.imputed_h5ad_path)} |",
        f"| evals.csv | {_fmt(ev.evals_csv_path)} |",
        "",
    ]
    return "\n".join(lines)


def render_card(rec: ModelRecord) -> str:
    """Return the markdown text for one model card."""
    title = rec.run_id
    family_label = {
        "scgen": "scGen",
        "impact_cellot": "IMPACT_CellOT",
        "cellot_celltype": "CellOT (cell-type framing, abandoned)",
        "cellot_legacy": "CellOT (legacy crossspecies)",
        "cellot_unresolved": "CellOT (unresolved — needs review)",
        "unknown": "unknown",
    }.get(rec.family, rec.family)

    figure_files = list_attached_figures(rec.model_dir)

    parts: list[str] = []
    parts.append(f"# {title}\n")
    parts.append(f"**Family**: {family_label}")
    if rec.family_alias_seen != rec.family:
        parts.append(f"   (alias on disk: `{rec.family_alias_seen}`)")
    parts.append("")
    parts.append(f"**Status**: `{rec.status}`")
    parts.append("")
    parts.append(f"**Model directory**: `{rec.model_dir}`")
    parts.append("")

    # Data provenance
    parts.append("## Data provenance\n")
    parts.append("| Field | Value |")
    parts.append("|---|---|")
    parts.append(f"| data_source | {_fmt(rec.data_source)} |")
    parts.append(f"| data_file | {_fmt(rec.data_file)} |")
    parts.append(f"| normalization | {_fmt(rec.normalization)} |")
    parts.append(f"| log1p_applied | {_fmt(rec.log1p_applied)} |")
    parts.append(f"| hvg_method | {_fmt(rec.hvg_method)} |")
    parts.append(f"| hvg_input_layer | {_fmt(rec.hvg_input_layer)} |")
    parts.append(f"| hvg_batch_key | {_fmt(rec.hvg_batch_key)} |")
    parts.append("")

    # Framing
    parts.append("## Framing\n")
    parts.append("| Field | Value |")
    parts.append("|---|---|")
    parts.append(f"| framing | {_fmt(rec.framing)} |")
    parts.append(f"| condition (column) | {_fmt(rec.condition)} |")
    parts.append(f"| source | {_fmt(rec.source)} |")
    parts.append(f"| target | {_fmt(rec.target)} |")
    parts.append(f"| transport direction | {_fmt(rec.transport_direction)} |")
    parts.append("")

    # Holdout
    parts.append("## Holdout\n")
    parts.append("| Field | Value |")
    parts.append("|---|---|")
    parts.append(f"| cell types | {_fmt(rec.holdout_cell_types)} |")
    parts.append(f"| species | {_fmt(rec.holdout_species)} |")
    parts.append(f"| train includes holdout | {_fmt(rec.train_includes_holdout)} |")
    parts.append(f"| datasplit strategy | {_fmt(rec.datasplit_strategy)} |")
    parts.append("")

    # Architecture
    parts.append("## Architecture\n")
    parts.append("| Field | Value |")
    parts.append("|---|---|")
    parts.append(f"| model class (library) | {_fmt(rec.model_name)} |")
    parts.append(f"| hidden_units | {_fmt(rec.hidden_units)} |")
    parts.append(f"| latent_dim | {_fmt(rec.latent_dim)} |")
    parts.append(f"| n_iters | {_fmt(rec.n_iters)} |")
    parts.append(f"| n_inner_iters | {_fmt(rec.n_inner_iters)} |")
    parts.append(f"| batch_size | {_fmt(rec.batch_size)} |")
    parts.append(f"| lr | {_fmt(rec.lr)} |")
    parts.append(f"| optimizer | {_fmt(rec.optimizer)} |")
    parts.append(f"| ae_emb path | {_fmt(rec.ae_emb_path)} |")
    parts.append("")

    # Lineage
    parts.append("## Lineage\n")
    parts.append("| Field | Value |")
    parts.append("|---|---|")
    parts.append(f"| generated_by | {_fmt(rec.generated_by)} |")
    parts.append(f"| created_at | {_fmt(rec.created_at)} |")
    parts.append(f"| last_modified | {_fmt(rec.last_modified)} |")
    parts.append("")

    # Diagnostic figures (populated by `./hub attach-figures` matcher)
    parts.append("## Diagnostic figures\n")
    if figure_files:
        # Show PNG/JPG inline; link PDFs and SVGs (markdown can't inline them).
        # Group by stem so a (png + pdf) pair displays as one entry with both links.
        from collections import defaultdict
        by_stem: dict[str, list[Path]] = defaultdict(list)
        for f in figure_files:
            by_stem[f.stem].append(f)
        for stem, files in sorted(by_stem.items()):
            parts.append(f"### {stem}\n")
            # Pick the first PNG/JPG (if any) for inline display.
            inline = next((f for f in files if f.suffix.lower() in {".png", ".jpg", ".jpeg"}), None)
            if inline is not None:
                parts.append(f"![{stem}]({inline.as_posix()})\n")
            # Link any other formats (PDF, SVG, additional PNG).
            other_links = [f for f in files if f != inline]
            if other_links:
                links = " · ".join(f"[`{f.suffix.lstrip('.')}`]({f.as_posix()})" for f in other_links)
                parts.append(f"_also available as: {links}_\n")
    else:
        parts.append("_None attached. Run `./hub attach-figures` to scan baseline/analysis/*_outputs/ and link matching figures here._")
        parts.append("")

    # Evaluations
    parts.append(f"## Evaluations ({len(rec.evals)})\n")
    if not rec.evals:
        parts.append("_No evaluations on disk yet._\n")
    else:
        for ev in rec.evals:
            parts.append(_eval_section(ev))

    if rec.notes:
        parts.append("## Notes\n")
        parts.append(rec.notes)
        parts.append("")

    parts.append("---")
    parts.append("")
    parts.append("_Generated by `speciesOT.hub` (v0.1). To regenerate: `./hub card " + rec.run_id + "`._")
    parts.append("")

    return "\n".join(parts)


def write_card(rec: ModelRecord, output_dir: Optional[Path] = None) -> Path:
    """Write a model card to disk. Returns the output path."""
    out_dir = output_dir or DEFAULT_CARDS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / run_id_to_filename(rec.run_id)
    out_path.write_text(render_card(rec))
    return out_path


# ---------------------------------------------------------------------------
# Comparison rendering (v0.7)
# ---------------------------------------------------------------------------

# Fields that are part of the "spec" — meaningful differences here are causes.
# Excludes: identity/path/lineage cosmetics, evaluations (compared separately),
# and free-form notes. Order chosen so the most-likely deltas appear first.
_SPEC_FIELDS: list[str] = [
    "family",
    "data_source",
    "normalization",
    "log1p_applied",
    "hvg_method",
    "hvg_input_layer",
    "hvg_batch_key",
    "data_file",
    "framing",
    "condition",
    "source",
    "target",
    "transport_direction",
    "holdout_cell_types",
    "holdout_species",
    "train_includes_holdout",
    "datasplit_strategy",
    "model_name",
    "hidden_units",
    "latent_dim",
    "n_iters",
    "n_inner_iters",
    "batch_size",
    "lr",
    "optimizer",
    "ae_emb_path",
    "status",
]


def _format_delta(a, b) -> str:
    """For numeric values, format the b-minus-a delta with sign. Else empty."""
    if isinstance(a, bool) or isinstance(b, bool):
        return ""  # bool deltas don't make sense
    try:
        d = float(b) - float(a)
    except (TypeError, ValueError):
        return ""
    if abs(d) < 0.0001:
        return "≈0"
    sign = "+" if d > 0 else ""
    if abs(d) < 0.01:
        return f"{sign}{d:.2e}"
    return f"{sign}{d:.4f}"


def render_comparison(a: ModelRecord, b: ModelRecord) -> str:
    """Return markdown text comparing two model records side-by-side."""
    parts: list[str] = []
    parts.append(f"# Comparison\n")
    parts.append(f"**A**: `{a.run_id}`")
    parts.append("")
    parts.append(f"**B**: `{b.run_id}`")
    parts.append("")

    # Spec deltas
    differences: list[tuple[str, object, object]] = []
    identical: list[str] = []
    for field in _SPEC_FIELDS:
        va = getattr(a, field, None)
        vb = getattr(b, field, None)
        if va == vb:
            identical.append(field)
        else:
            differences.append((field, va, vb))

    parts.append("## Spec differences (the \"cause\")\n")
    if not differences:
        parts.append("_No spec-level differences. These two models have identical specs._")
        parts.append("")
    else:
        parts.append("| Field | A | B |")
        parts.append("|---|---|---|")
        for field, va, vb in differences:
            parts.append(f"| `{field}` | {_fmt(va)} | {_fmt(vb)} |")
        parts.append("")

    # Metric deltas, per eval_id
    parts.append("## Metric differences (the \"effect\")\n")
    a_evals = {ev.eval_id: ev for ev in a.evals}
    b_evals = {ev.eval_id: ev for ev in b.evals}
    common_evals = sorted(set(a_evals.keys()) & set(b_evals.keys()))
    a_only = sorted(set(a_evals.keys()) - set(b_evals.keys()))
    b_only = sorted(set(b_evals.keys()) - set(a_evals.keys()))

    if not common_evals and not a_only and not b_only:
        parts.append("_Neither model has any evaluations on disk._")
        parts.append("")
    else:
        if common_evals:
            for eval_id in common_evals:
                ea, eb = a_evals[eval_id], b_evals[eval_id]
                parts.append(f"### `{eval_id}`\n")
                parts.append("| Metric | A | B | Δ (B − A) |")
                parts.append("|---|---|---|---|")
                parts.append(
                    f"| R² of means | {_fmt(ea.headline_r2_means)} | {_fmt(eb.headline_r2_means)} | "
                    f"{_format_delta(ea.headline_r2_means, eb.headline_r2_means)} |"
                )
                parts.append(
                    f"| MMD | {_fmt(ea.headline_mmd)} | {_fmt(eb.headline_mmd)} | "
                    f"{_format_delta(ea.headline_mmd, eb.headline_mmd)} |"
                )
                if ea.frac_gap_closed is not None or eb.frac_gap_closed is not None:
                    parts.append(
                        f"| fraction of gap closed | {_fmt(ea.frac_gap_closed)} | {_fmt(eb.frac_gap_closed)} | "
                        f"{_format_delta(ea.frac_gap_closed, eb.frac_gap_closed)} |"
                    )
                if ea.headline_js is not None or eb.headline_js is not None:
                    parts.append(
                        f"| mean per-gene JS | {_fmt(ea.headline_js)} | {_fmt(eb.headline_js)} | "
                        f"{_format_delta(ea.headline_js, eb.headline_js)} |"
                    )
                parts.append(
                    f"| n_cells present | {_fmt(ea.n_cells_present)} | {_fmt(eb.n_cells_present)} | — |"
                )
                parts.append("")
        if a_only:
            parts.append(f"_Only in A_: {', '.join(f'`{e}`' for e in a_only)}\n")
        if b_only:
            parts.append(f"_Only in B_: {', '.join(f'`{e}`' for e in b_only)}\n")

    if identical:
        parts.append("## Identical fields\n")
        parts.append(", ".join(f"`{f}`" for f in identical))
        parts.append("")

    parts.append("---")
    parts.append("")
    parts.append("_Generated by `speciesOT.hub.render.render_comparison` (v0.7)._")
    parts.append("")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Export (CSV / MD) — replaces scripts/build_experiments_inventory.py
# ---------------------------------------------------------------------------

# Columns for the flat CSV export. Order chosen so the most-useful fields appear first.
_EXPORT_COLUMNS: list[str] = [
    "run_id",
    "family",
    "family_alias_seen",
    "status",
    "data_source",
    "normalization",
    "hvg_method",
    "hvg_input_layer",
    "log1p_applied",
    "hvg_batch_key",
    "data_file",
    "framing",
    "condition",
    "source",
    "target",
    "transport_direction",
    "holdout_cell_types",
    "holdout_species",
    "train_includes_holdout",
    "datasplit_strategy",
    "model_name",
    "hidden_units",
    "latent_dim",
    "n_iters",
    "n_inner_iters",
    "batch_size",
    "lr",
    "optimizer",
    "ae_emb_path",
    "generated_by",
    "created_at",
    "last_modified",
    "model_dir",
    "n_evals",
    "evals_summary",
]


def _csv_value(v) -> str:
    """Stringify a value for CSV. Lists become 'a;b;c' (semicolon-separated)."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, list):
        return ";".join(str(x) for x in v)
    if isinstance(v, Path):
        return str(v)
    return str(v)


def _evals_summary(rec: ModelRecord) -> str:
    """One-line summary of evaluations for the CSV/MD export."""
    if not rec.evals:
        return ""
    bits = []
    for ev in rec.evals:
        r2 = f"{ev.headline_r2_means:.3f}" if ev.headline_r2_means is not None else "—"
        mmd = f"{ev.headline_mmd:.3f}" if ev.headline_mmd is not None else "—"
        bits.append(f"{ev.eval_id}: R²={r2} MMD={mmd}")
    return " | ".join(bits)


def export_csv(records: list[ModelRecord], out_path: Path) -> Path:
    """Write a flat CSV with one row per ModelRecord. Replaces experiments_inventory.csv."""
    import csv
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_EXPORT_COLUMNS)
        writer.writeheader()
        for rec in sorted(records, key=lambda r: r.run_id):
            row = {col: _csv_value(getattr(rec, col, None)) for col in _EXPORT_COLUMNS if col not in {"n_evals", "evals_summary"}}
            row["n_evals"] = str(len(rec.evals))
            row["evals_summary"] = _evals_summary(rec)
            writer.writerow(row)
    return out_path


def export_md(records: list[ModelRecord], out_path: Path) -> Path:
    """Write a human-readable markdown summary. Replaces experiments_inventory.md."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# experiments_inventory",
        "",
        f"Auto-generated from `./hub export md` ({len(records)} models).",
        "",
        "Same data as `experiments_inventory.csv`. Grouped by family for browsability.",
        "",
    ]

    # Group by family.
    by_family: dict[str, list[ModelRecord]] = {}
    for r in sorted(records, key=lambda r: r.run_id):
        by_family.setdefault(r.family, []).append(r)

    family_labels = {
        "scgen": "scGen",
        "impact_cellot": "IMPACT_CellOT",
        "cellot_celltype": "CellOT (cell-type framing, abandoned)",
        "cellot_legacy": "CellOT (legacy crossspecies)",
        "cellot_unresolved": "CellOT (unresolved)",
        "unknown": "Unknown",
    }
    family_order = ["impact_cellot", "scgen", "cellot_celltype", "cellot_legacy", "cellot_unresolved", "unknown"]

    for fam in family_order:
        if fam not in by_family:
            continue
        members = by_family[fam]
        lines.append(f"## {family_labels.get(fam, fam)} ({len(members)})")
        lines.append("")
        lines.append("| run_id | hvg | holdout | mode | R² | MMD | status |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in members:
            hvg = r.hvg_method or "—"
            if r.holdout_cell_types:
                holdout = ", ".join(r.holdout_cell_types)
            elif r.holdout_species:
                holdout = f"species={r.holdout_species}"
            else:
                holdout = "—"
            if r.train_includes_holdout is True:
                mode = "iid"
            elif r.train_includes_holdout is False:
                mode = "ood"
            else:
                mode = "—"
            # Headline metrics: prefer data_space
            r2_str = "—"
            mmd_str = "—"
            if r.evals:
                ds = [e for e in r.evals if e.space == "data_space"]
                ev = (ds + r.evals)[0]
                if ev.headline_r2_means is not None:
                    r2_str = f"{ev.headline_r2_means:.3f}"
                if ev.headline_mmd is not None:
                    mmd_str = f"{ev.headline_mmd:.3f}"
            lines.append(
                f"| `{r.run_id}` | `{hvg}` | {holdout} | {mode} | {r2_str} | {mmd_str} | {r.status} |"
            )
        lines.append("")

    out_path.write_text("\n".join(lines))
    return out_path


def write_index(records: list[ModelRecord], output_dir: Optional[Path] = None) -> Path:
    """Write a top-level INDEX.md linking to every card."""
    out_dir = output_dir or DEFAULT_CARDS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "INDEX.md"

    # Group by family for browsability.
    by_family: dict[str, list[ModelRecord]] = {}
    for r in sorted(records, key=lambda r: r.run_id):
        by_family.setdefault(r.family, []).append(r)

    family_order = [
        "impact_cellot",
        "scgen",
        "cellot_celltype",
        "cellot_legacy",
        "cellot_unresolved",
        "unknown",
    ]
    family_labels = {
        "scgen": "scGen",
        "impact_cellot": "IMPACT_CellOT",
        "cellot_celltype": "CellOT (cell-type framing, abandoned)",
        "cellot_legacy": "CellOT (legacy crossspecies)",
        "cellot_unresolved": "CellOT (unresolved)",
        "unknown": "Unknown",
    }

    lines = [
        "# Model card index",
        "",
        f"Auto-generated catalog of {len(records)} models. Grouped by family.",
        "",
        "Regenerate: `./hub card --all`.",
        "",
    ]

    for fam in family_order:
        if fam not in by_family:
            continue
        members = by_family[fam]
        lines.append(f"## {family_labels.get(fam, fam)} ({len(members)})")
        lines.append("")
        for r in members:
            fname = run_id_to_filename(r.run_id)
            metric_bit = ""
            if r.evals:
                # Prefer data_space, fall back to first eval.
                ds = [e for e in r.evals if e.space == "data_space"]
                ev = (ds + r.evals)[0]
                if ev.headline_r2_means is not None:
                    metric_bit = f" — R²={ev.headline_r2_means:.3f}"
                    if ev.headline_mmd is not None:
                        metric_bit += f", MMD={ev.headline_mmd:.3f}"
            holdout = ""
            if r.holdout_cell_types:
                holdout = " · holdout " + ",".join(r.holdout_cell_types)
            elif r.holdout_species:
                holdout = f" · holdout species={r.holdout_species}"
            lines.append(f"- [`{r.run_id}`]({fname}){holdout}{metric_bit}")
        lines.append("")

    out_path.write_text("\n".join(lines))
    return out_path
