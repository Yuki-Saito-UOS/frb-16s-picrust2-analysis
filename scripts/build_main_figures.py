from __future__ import annotations

import argparse
import os
from pathlib import Path
from shutil import copy2
from textwrap import fill

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp")

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd
from pypdf import PdfReader, PdfWriter
from scipy.stats import kruskal

from ricebran_analysis.config import ProjectPaths, load_config


mpl.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "Arial", "font.size": 9})

GROUP_LABELS = {"control": "Ctrl", "ricebran": "RB", "Fermented_ricebran": "FRB"}
FIGURE4_TAXA = ["F_Lactobacillaceae", "A2", "Lachnospiraceae_NK4A136_group", "Lachnospiraceae_UCG-006"]
FIGURE5_HEATMAP_PATHWAYS = ["ALL-CHORISMATE-PWY", "PWY-6629", "KDO-NAGLIPASYN-PWY", "THREOCAT-PWY", "LPSSYN-PWY"]
FIGURE5_CONTRIBUTOR_PATHWAYS = ["ALL-CHORISMATE-PWY", "PWY-6629"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the primary FRB 16S rRNA Figures 4 and 5.")
    parser.add_argument("--config", type=Path, default=Path("config/frb.toml"))
    parser.add_argument("--base-dir", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, default=Path("results/frb"))
    parser.add_argument("--figures-dir", type=Path, default=Path("figures"))
    parser.add_argument("--top-n-genera", type=int, default=15)
    return parser


def read_raw_genus_table(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, sep="\t", skiprows=1)
    feature_col = frame.columns[0]
    sample_cols = [column for column in frame.columns if column != feature_col]

    def label(taxon: str) -> str:
        ranks = {}
        for part in str(taxon).split(";"):
            part = part.strip()
            if "__" in part:
                rank, value = part.split("__", 1)
                ranks[rank] = value.strip()
        if ranks.get("g"):
            return ranks["g"]
        if ranks.get("f"):
            return f"F_{ranks['f']}"
        return "Unclassified"

    frame["resolved_taxon"] = frame[feature_col].map(label)
    return frame[["resolved_taxon", *sample_cols]].groupby("resolved_taxon", as_index=False).sum(numeric_only=True)


def sample_relative_abundance(taxa: pd.DataFrame, samples: list[str]) -> pd.DataFrame:
    indexed = taxa.set_index("resolved_taxon")
    values = indexed.reindex(columns=samples, fill_value=0.0).apply(pd.to_numeric, errors="coerce").fillna(0.0)
    return values.div(values.sum(axis=0).replace(0.0, np.nan), axis=1).fillna(0.0)


def group_mean_composition(relative: pd.DataFrame, groups: dict[str, list[str]]) -> pd.DataFrame:
    values = {}
    for group, samples in groups.items():
        present = [sample for sample in samples if sample in relative.columns]
        values[group] = relative[present].mean(axis=1) if present else pd.Series(0.0, index=relative.index)
    return pd.DataFrame(values)


def group_p_value(values: pd.Series, groups: dict[str, list[str]]) -> float:
    grouped = [values.reindex(samples).dropna().to_numpy() for samples in groups.values()]
    return float(kruskal(*grouped).pvalue)


def add_significance_label(ax: plt.Axes, p_value: float) -> None:
    if p_value >= 0.05:
        return
    lower, upper = ax.get_ylim()
    height = upper - lower
    y = upper - 0.10 * height
    ax.plot([1, 1, 3, 3], [y - 0.02 * height, y, y, y - 0.02 * height], color="black", linewidth=0.9)
    ax.text(2, y + 0.02 * height, "*", ha="center", va="bottom", fontsize=12)


def build_figure4(
    *,
    relative: pd.DataFrame,
    groups: dict[str, list[str]],
    out_path: Path,
    top_n_genera: int,
) -> None:
    group_order = list(groups)
    fig = plt.figure(figsize=(8.3, 7.2))
    outer = fig.add_gridspec(3, 1, height_ratios=[0.62, 0.78, 1.0], hspace=0.28)
    ax_composition = fig.add_subplot(outer[0])
    ax_legend = fig.add_subplot(outer[1])
    bottom = outer[2].subgridspec(1, len(FIGURE4_TAXA), wspace=0.55)

    group_means = group_mean_composition(relative, groups)
    top_taxa = group_means.mean(axis=1).sort_values(ascending=False).head(top_n_genera).index.tolist()
    composition = group_means.loc[top_taxa].copy()
    composition.loc["Other"] = (1.0 - composition.sum(axis=0)).clip(lower=0.0)
    colors = list(plt.get_cmap("tab20").colors)
    left = np.zeros(len(group_order))
    for index, taxon in enumerate(composition.index):
        values = composition.loc[taxon, group_order].to_numpy()
        ax_composition.barh(np.arange(len(group_order)), values, left=left, color=("#B8B8B8" if taxon == "Other" else colors[index % len(colors)]), edgecolor="white", linewidth=0.35, label=taxon)
        left += values
    ax_composition.set_yticks(np.arange(len(group_order)), [GROUP_LABELS[group] for group in group_order])
    ax_composition.invert_yaxis()
    ax_composition.set_xlim(0, 1)
    ax_composition.xaxis.set_major_formatter(PercentFormatter(1.0))
    ax_legend.axis("off")
    handles, labels = ax_composition.get_legend_handles_labels()
    ax_legend.legend(handles, labels, ncol=3, frameon=False, loc="center left", fontsize=6.5, columnspacing=0.9, handlelength=0.9)

    rng = np.random.default_rng(0)
    taxon_axes = [fig.add_subplot(bottom[index]) for index in range(len(FIGURE4_TAXA))]
    for ax, taxon in zip(taxon_axes, FIGURE4_TAXA):
        values = relative.loc[taxon] if taxon in relative.index else pd.Series(0.0, index=relative.columns)
        data = [values.reindex(groups[group]).fillna(0.0).to_numpy() * 100 for group in group_order]
        box = ax.boxplot(data, patch_artist=True, showfliers=False, widths=0.55)
        for patch in box["boxes"]:
            patch.set(facecolor="white", edgecolor="black")
        for index, group_values in enumerate(data, start=1):
            ax.scatter(index + rng.uniform(-0.08, 0.08, len(group_values)), group_values, color="black", s=10, zorder=3)
        ax.set_title(fill(taxon.replace("F_", ""), width=18), fontsize=8, pad=8)
        ax.set_xticks(range(1, len(group_order) + 1), [GROUP_LABELS[group] for group in group_order], rotation=45)
        if ax is taxon_axes[0]:
            ax.set_ylabel("Relative abundance (%)")
        add_significance_label(ax, group_p_value(values * 100, groups))

    fig.text(0.95, 0.975, "Figure 4", ha="right", va="top", fontsize=12)
    fig.subplots_adjust(left=0.12, right=0.96, top=0.92, bottom=0.10)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)


def read_table(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


def zscore_rows(table: pd.DataFrame) -> pd.DataFrame:
    values = table.to_numpy(dtype=float)
    means = np.nanmean(values, axis=1, keepdims=True)
    stds = np.nanstd(values, axis=1, keepdims=True)
    stds[stds == 0] = 1.0
    return pd.DataFrame((values - means) / stds, index=table.index, columns=table.columns)


def build_figure5(
    *,
    pathway_abundance: pd.DataFrame,
    annotations: pd.DataFrame,
    ranked_contributors: pd.DataFrame,
    groups: dict[str, list[str]],
    out_path: Path,
) -> None:
    annotation_map = annotations.set_index("pathway")["pathway_name"].to_dict()
    samples = [sample for group in groups.values() for sample in group if sample in pathway_abundance.columns]
    sample_labels = [
        f"{GROUP_LABELS[group]}{index + 1}"
        for group, names in groups.items()
        for index, sample in enumerate(names)
        if sample in pathway_abundance.columns
    ]
    heatmap_pathways = [pathway for pathway in FIGURE5_HEATMAP_PATHWAYS if pathway in pathway_abundance.index]
    heatmap = zscore_rows(pathway_abundance.loc[heatmap_pathways, samples])
    heatmap.index = [annotation_map.get(pathway, pathway) for pathway in heatmap_pathways]

    fig = plt.figure(figsize=(8.3, 10.8))
    grid = fig.add_gridspec(3, 1, height_ratios=[0.72, 0.38, 0.70], hspace=0.42)
    ax_heatmap = fig.add_subplot(grid[0])
    image = ax_heatmap.imshow(heatmap, aspect="auto", cmap="RdBu_r", vmin=-2.5, vmax=2.5)
    ax_heatmap.set_yticks(range(len(heatmap.index)), [fill(label, 48) for label in heatmap.index], fontsize=7)
    ax_heatmap.set_xticks(range(len(samples)), sample_labels, rotation=45, ha="right")
    for boundary in np.cumsum([len(names) for names in groups.values()])[:-1]:
        ax_heatmap.axvline(boundary - 0.5, color="white", linewidth=1.2)
    colorbar = fig.colorbar(image, ax=ax_heatmap, fraction=0.025, pad=0.02)
    colorbar.set_label("Row z-score")
    ax_heatmap.text(0.98, 1.12, "Figure 5", transform=ax_heatmap.transAxes, ha="right", va="top", fontsize=12)

    source = ranked_contributors[ranked_contributors["source_table"].eq("pathway_stats_3group.tsv")].copy()
    source = source[source["pathway"].isin(FIGURE5_CONTRIBUTOR_PATHWAYS)]
    if source.empty:
        raise RuntimeError("No three-group ranked contributors found for the Figure 5 pathways.")
    pathways = [pathway for pathway in FIGURE5_CONTRIBUTOR_PATHWAYS if pathway in set(source["pathway"])]
    totals = source.groupby("pathway")["target_group_total"].first().reindex(pathways)
    taxa = source.groupby("resolved_taxon")["target_group_mean"].sum().sort_values(ascending=False).head(15).index.tolist()
    ax_stack = fig.add_subplot(grid[1])
    left = np.zeros(len(pathways))
    palette = list(plt.get_cmap("tab20").colors)
    for index, taxon in enumerate(taxa):
        values = source[source["resolved_taxon"].eq(taxon)].groupby("pathway")["target_group_mean"].sum().reindex(pathways, fill_value=0.0).to_numpy()
        fraction = values / totals.to_numpy()
        ax_stack.barh(np.arange(len(pathways)), fraction, left=left, color=palette[index % len(palette)], edgecolor="white", linewidth=0.35, label=taxon)
        left += fraction
    ax_stack.barh(np.arange(len(pathways)), np.maximum(1.0 - left, 0.0), left=left, color="#B8B8B8", edgecolor="white", linewidth=0.35, label="Other")
    ax_stack.set_yticks(np.arange(len(pathways)), [annotation_map.get(pathway, pathway) for pathway in pathways], fontsize=7)
    ax_stack.set_xlim(0, 1)
    ax_stack.xaxis.set_major_formatter(PercentFormatter(1.0))
    ax_stack.set_xlabel("Relative contribution in FRB")

    ax_legend = fig.add_subplot(grid[2])
    ax_legend.axis("off")
    handles, labels = ax_stack.get_legend_handles_labels()
    ax_legend.legend(handles, labels, ncol=3, frameon=False, loc="center left", fontsize=7, columnspacing=1.0, handlelength=1.0)

    fig.subplots_adjust(left=0.30, right=0.94, top=0.94, bottom=0.08)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)


def combine_figures(figures: list[Path], out_path: Path) -> None:
    """Combine vector figure pages without rasterizing their editable elements."""
    writer = PdfWriter()
    for figure in figures:
        reader = PdfReader(str(figure))
        for page in reader.pages:
            writer.add_page(page)
    with out_path.open("wb") as handle:
        writer.write(handle)


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    paths = ProjectPaths(
        base_dir=args.base_dir.resolve(),
        out_dir=args.results_dir.resolve(),
        qiime_dirname=config.qiime_dirname,
        picrust2_dirname=config.picrust2_dirname,
        results_dirname=config.results_dirname,
    )
    figures_dir = args.figures_dir.resolve()
    q2_dir = paths.configured_qiime_dir
    genus_table = read_raw_genus_table(q2_dir / "table-genus.tsv")
    relative = sample_relative_abundance(genus_table, [sample for samples in config.groups.values() for sample in samples])
    figure4 = figures_dir / "figure4_16s_community_structure.pdf"
    build_figure4(relative=relative, groups=config.groups, out_path=figure4, top_n_genera=args.top_n_genera)

    results_dir = args.results_dir.resolve()
    abundance = read_table(paths.pathway_unstrat).set_index("pathway")
    annotations = read_table(results_dir / "annotations" / "pathway_annotations.tsv")
    contributors = read_table(results_dir / "primary_pathway_genus_ranked.tsv")
    figure5 = figures_dir / "figure5_predicted_metagenome.pdf"
    build_figure5(pathway_abundance=abundance, annotations=annotations, ranked_contributors=contributors, groups=config.groups, out_path=figure5)
    combined = figures_dir / "frb_primary_figures_4_5.pdf"
    combine_figures([figure4, figure5], combined)

    external_dir = paths.base_dir / "ricebran_figures"
    external_dir.mkdir(parents=True, exist_ok=True)
    for figure in [figure4, figure5, combined]:
        copy2(figure, external_dir / figure.name)
    print(f"Saved: {figure4}")
    print(f"Saved: {figure5}")
    print(f"Saved: {combined}")


if __name__ == "__main__":
    main()
