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
