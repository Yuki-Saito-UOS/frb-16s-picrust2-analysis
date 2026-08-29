"""Rank genus-level FRB contributors for the two public Figure 5 pathways."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from ricebran_analysis.config import ProjectPaths, load_config
from ricebran_analysis.io import sample_to_group


PRIMARY_PATHWAYS = ("ALL-CHORISMATE-PWY", "PWY-6629")
SOURCE_TABLE = "pathway_stats_3group.tsv"
FRB_GROUP = "Fermented_ricebran"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rank genus contributors for the public FRB Figure 5 pathways.")
    parser.add_argument("--config", type=Path, default=Path("config/frb.toml"))
    parser.add_argument("--base-dir", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--top-n", type=int, default=20)
    return parser


def read_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, sep="\t")


def load_contributions(path: Path) -> pd.DataFrame:
    table = read_table(path).rename(columns={"taxon_function_abun": "value"})
    required = {"sample", "function", "taxon", "value"}
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"Missing columns in {path}: {sorted(missing)}")
    table["sample"] = table["sample"].astype(str).str.strip()
    table["function"] = table["function"].astype(str).str.strip()
    table["taxon"] = table["taxon"].astype(str).str.strip()
    table["value"] = pd.to_numeric(table["value"], errors="coerce").fillna(0.0)
    return table


def resolve_taxon_label(row: pd.Series) -> str:
    for column, prefix in (("genus", ""), ("family", "F_"), ("order", ""), ("class_", ""), ("phylum", ""), ("domain", "")):
        value = str(row.get(column, "")).strip()
        if value and value.lower() not in {"nan", "none"}:
            return f"{prefix}{value}"
    return "Unclassified"


def validate_groups(table: pd.DataFrame, groups: dict[str, list[str]]) -> dict[str, int]:
    configured = [sample for samples in groups.values() for sample in samples]
    if len(configured) != len(set(configured)):
        raise ValueError("A sample is assigned to more than one group.")
    observed = set(table["sample"])
    unknown = sorted(observed - set(configured))
    missing = sorted(set(configured) - observed)
    if unknown or missing:
        raise ValueError(f"Contribution sample mismatch; unknown={unknown}, missing={missing}")
    return {group: len(samples) for group, samples in groups.items()}


def rank_primary_contributors(
    contributions: pd.DataFrame,
    pathway_rows: pd.DataFrame,
    *,
    group_sizes: dict[str, int],
    top_n: int,
) -> pd.DataFrame:
    if top_n < 1:
        raise ValueError("top_n must be at least 1.")
    ranked: list[pd.DataFrame] = []
    for _, pathway_row in pathway_rows.iterrows():
        pathway = str(pathway_row["pathway"])
        subset = contributions[contributions["function"].eq(pathway)]
        grouped = subset.groupby(["resolved_taxon", "group"], as_index=False)["value"].sum()
        grouped["value"] = grouped["value"] / grouped["group"].map(group_sizes)
        means = grouped.pivot_table(index="resolved_taxon", columns="group", values="value", fill_value=0.0)
        for group in group_sizes:
            if group not in means:
                means[group] = 0.0
        means = means.reset_index()
        means["target_group_mean"] = means[FRB_GROUP]
        total = means["target_group_mean"].sum()
        means["target_group_total"] = total
        means["target_group_fraction"] = means["target_group_mean"] / total if total else 0.0
        means["rank"] = means["target_group_mean"].rank(method="dense", ascending=False).astype(int)
        means = means.sort_values(["target_group_mean", "resolved_taxon"], ascending=[False, True]).head(top_n).copy()
        means.insert(0, "source_table", SOURCE_TABLE)
        means.insert(1, "pathway", pathway)
        means.insert(2, "pathway_name", pathway_row["pathway_name"])
        means.insert(3, "target_group", FRB_GROUP)
        ranked.append(means)
    return pd.concat(ranked, ignore_index=True)


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    paths = ProjectPaths(
        base_dir=args.base_dir.expanduser().resolve(),
        out_dir=args.results_dir.expanduser().resolve(),
        qiime_dirname=config.qiime_dirname,
        picrust2_dirname=config.picrust2_dirname,
        results_dirname=config.results_dirname,
    )
    results_dir = args.results_dir.expanduser().resolve()
    annotations = read_table(results_dir / "annotations" / "pathway_annotations.tsv")
    statistics = read_table(results_dir / SOURCE_TABLE)
    pathway_rows = statistics.merge(annotations[["pathway", "pathway_name"]], on="pathway", how="left")
    pathway_rows = pathway_rows[pathway_rows["pathway"].isin(PRIMARY_PATHWAYS)].copy()
    if set(pathway_rows["pathway"]) != set(PRIMARY_PATHWAYS):
        raise RuntimeError("The two public Figure 5 pathways were not found in the three-group statistics table.")
    if not pathway_rows["max_mean_group"].eq(FRB_GROUP).all():
        raise RuntimeError("The public Figure 5 contributor bars require FRB to be the highest-mean group.")

    contributions = load_contributions(paths.pathway_contrib)
    group_sizes = validate_groups(contributions, config.groups)
    taxonomy = read_table(results_dir / "annotations" / "taxonomy_annotations.tsv")
    contributions = contributions.merge(taxonomy, left_on="taxon", right_on="feature_id", how="left")
    contributions["group"] = contributions["sample"].map(lambda sample: sample_to_group(sample, config.groups))
    contributions["resolved_taxon"] = contributions.apply(resolve_taxon_label, axis=1)
    output = rank_primary_contributors(contributions, pathway_rows, group_sizes=group_sizes, top_n=args.top_n)

    output_path = results_dir / "primary_pathway_genus_ranked.tsv"
    output.to_csv(output_path, sep="\t", index=False)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
