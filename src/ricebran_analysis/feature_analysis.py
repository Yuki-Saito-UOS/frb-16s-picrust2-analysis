from __future__ import annotations

from itertools import combinations
from pathlib import Path
import re

import pandas as pd

from .config import AnalysisConfig
from .stats import compare_three_groups, compare_two_groups, select_top_features


def _filename_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")


def write_feature_outputs(
    table: pd.DataFrame,
    feature_col: str,
    stats_prefix: str,
    top_prefix: str,
    out_dir: Path,
    config: AnalysisConfig,
) -> dict[str, Path]:
    outputs: dict[str, Path] = {}

    if len(config.groups) >= 3:
        three_group_stats = compare_three_groups(table, config.groups, feature_col)
        stats_key = f"{stats_prefix}_stats_3group"
        outputs[stats_key] = out_dir / f"{stats_prefix}_stats_3group.tsv"
        three_group_stats.to_csv(outputs[stats_key], sep="\t", index=False)

        top_three_group = select_top_features(
            three_group_stats,
            feature_col,
            config.p_value,
            config.effect,
            config.top_n,
        )
        top_key = f"top_{top_prefix}_3group"
        outputs[top_key] = out_dir / f"TOP_{top_prefix}_3group.tsv"
        top_three_group.to_csv(outputs[top_key], sep="\t", index=False)

    for group_a, group_b in combinations(config.groups, 2):
        comparison = f"{_filename_token(group_a)}_vs_{_filename_token(group_b)}"
        two_group_stats = compare_two_groups(table, config.groups, feature_col, group_a, group_b)

        stats_key = f"{stats_prefix}_stats_2group_{comparison}"
        outputs[stats_key] = out_dir / f"{stats_prefix}_stats_2group_{comparison}.tsv"
        two_group_stats.to_csv(outputs[stats_key], sep="\t", index=False)

        top_two_group = select_top_features(
            two_group_stats,
            feature_col,
            config.p_value,
            config.effect,
            config.top_n,
        )
        top_key = f"top_{top_prefix}_2group_{comparison}"
        outputs[top_key] = out_dir / f"TOP_{top_prefix}_2group_{comparison}.tsv"
        top_two_group.to_csv(outputs[top_key], sep="\t", index=False)

    return outputs
