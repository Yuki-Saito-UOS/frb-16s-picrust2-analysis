from __future__ import annotations

from pathlib import Path

from .config import AnalysisConfig
from .feature_analysis import write_feature_outputs
from .io import read_genus_table


def analyze_genus(genus_table: Path, out_dir: Path, config: AnalysisConfig) -> dict[str, Path]:
    genus = read_genus_table(genus_table)
    return write_feature_outputs(
        genus,
        feature_col="genus",
        stats_prefix="genus",
        top_prefix="genus",
        out_dir=out_dir,
        config=config,
    )
