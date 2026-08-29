"""Export the minimum processed CSV datasets needed to reproduce Figures 4 and 5.

The exported files contain anonymized within-study sample labels only. They are
derived from local QIIME2/PICRUSt2 outputs and are suitable for public release;
raw reads, QIIME2 artifacts, and study metadata are intentionally not copied.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from build_main_figures import (
    FIGURE4_TAXA,
    FIGURE5_CONTRIBUTOR_PATHWAYS,
    FIGURE5_HEATMAP_PATHWAYS,
    GROUP_LABELS,
    read_raw_genus_table,
    sample_relative_abundance,
)
from ricebran_analysis.config import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export public processed FRB figure datasets as CSV.")
    parser.add_argument("--config", type=Path, default=Path("config/frb.toml"))
    parser.add_argument("--base-dir", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    return parser


def public_sample_table(groups: dict[str, list[str]]) -> pd.DataFrame:
    rows = []
    for group, samples in groups.items():
        for index, sample in enumerate(samples, start=1):
            rows.append({"source_sample_id": sample, "sample_id": f"{GROUP_LABELS[group]}{index}", "group": GROUP_LABELS[group]})
    return pd.DataFrame(rows)


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    base_dir = args.base_dir.resolve()
    results_dir = args.results_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    samples = public_sample_table(config.groups)
    samples[["sample_id", "group"]].to_csv(output_dir / "sample_groups.csv", index=False)
    sample_map = samples.set_index("source_sample_id")["sample_id"].to_dict()
    source_samples = samples["source_sample_id"].tolist()

    genus = read_raw_genus_table(base_dir / config.qiime_dirname / "table-genus.tsv")
    relative = sample_relative_abundance(genus, source_samples).rename(columns=sample_map)
    relative.index.name = "resolved_taxon"
    relative.reset_index().to_csv(output_dir / "genus_relative_abundance.csv", index=False)

    displayed_taxa = relative.reindex(FIGURE4_TAXA, fill_value=0.0).reset_index().melt(
        id_vars="resolved_taxon", var_name="sample_id", value_name="relative_abundance"
    )
    displayed_taxa["relative_abundance_percent"] = displayed_taxa.pop("relative_abundance") * 100
    displayed_taxa = displayed_taxa.merge(samples[["sample_id", "group"]], on="sample_id", how="left")
    displayed_taxa.to_csv(output_dir / "figure4_display_taxa.csv", index=False)

    pathway_source = base_dir / config.qiime_dirname / config.picrust2_dirname / "pathways_out" / "path_abun_unstrat.tsv.gz"
    pathways = pd.read_csv(pathway_source, sep="\t").set_index("pathway")
    pathways = pathways.reindex(FIGURE5_HEATMAP_PATHWAYS).rename(columns=sample_map)
    pathways.index.name = "pathway"
    pathways.reset_index().to_csv(output_dir / "figure5_selected_pathway_abundance.csv", index=False)

    ranked = pd.read_csv(results_dir / "primary_pathway_genus_ranked.tsv", sep="\t")
    contributions = ranked.loc[
        ranked["source_table"].eq("pathway_stats_3group.tsv")
        & ranked["pathway"].isin(FIGURE5_CONTRIBUTOR_PATHWAYS),
        ["pathway", "pathway_name", "resolved_taxon", "target_group", "target_group_mean", "target_group_total", "target_group_fraction", "rank"],
    ].copy()
    contributions.rename(columns={"target_group_mean": "frb_group_mean_contribution"}, inplace=True)
    contributions.to_csv(output_dir / "figure5_frb_taxon_contributions.csv", index=False)

    print(f"Saved public processed datasets to: {output_dir}")


if __name__ == "__main__":
    main()
