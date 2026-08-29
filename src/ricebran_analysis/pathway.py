from __future__ import annotations

from pathlib import Path

from .config import AnalysisConfig
from .feature_analysis import write_feature_outputs
from .io import read_feature_table


def analyze_pathways(pathway_table: Path, out_dir: Path, config: AnalysisConfig) -> dict[str, Path]:
    pathways = read_feature_table(pathway_table, "pathway")
    return write_feature_outputs(
        pathways,
        feature_col="pathway",
        stats_prefix="pathway",
        top_prefix="pathways",
        out_dir=out_dir,
        config=config,
    )
