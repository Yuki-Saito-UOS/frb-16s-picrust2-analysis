from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pandas as pd


def _qza_data_name(archive: ZipFile, path: Path, suffix: str) -> str:
    matches = [name for name in archive.namelist() if name.endswith(suffix)]
    if len(matches) != 1:
        raise ValueError(f"Expected one {suffix!r} entry in {path}, found {len(matches)}.")
    return matches[0]


def read_alpha_diversity_qza(path: Path) -> pd.DataFrame:
    """Read the sample-level alpha-diversity table embedded in a QIIME2 artifact."""
    with ZipFile(path) as archive:
        with archive.open(_qza_data_name(archive, path, "/data/alpha-diversity.tsv")) as handle:
            frame = pd.read_csv(handle, sep="\t", index_col=0)
    frame.index.name = "sample"
    return frame


def read_pcoa_qza(path: Path) -> tuple[pd.DataFrame, pd.Series]:
    """Read sample coordinates and explained variance from a QIIME2 PCoA artifact."""
    with ZipFile(path) as archive:
        with archive.open(_qza_data_name(archive, path, "/data/ordination.txt")) as handle:
            lines = [line.decode("utf-8").rstrip("\n") for line in handle if line.strip()]

    site_index = next((i for i, line in enumerate(lines) if line.startswith("Site\t")), None)
    proportion_index = next((i for i, line in enumerate(lines) if line.startswith("Proportion explained\t")), None)
    if site_index is None or proportion_index is None:
        raise ValueError(f"QIIME2 PCoA artifact has an unexpected ordination format: {path}")

    explained = pd.Series(
        [float(value) for value in lines[proportion_index + 1].split("\t")],
        index=[f"PC{i + 1}" for i in range(len(lines[proportion_index + 1].split("\t")))],
        name="proportion_explained",
    )
    parts = lines[site_index].split("\t")
    n_samples, n_axes = int(parts[1]), int(parts[2])
    rows = [line.split("\t") for line in lines[site_index + 1 : site_index + 1 + n_samples]]
    if len(rows) != n_samples:
        raise ValueError(f"Expected {n_samples} PCoA samples in {path}, found {len(rows)}.")
    coordinates = pd.DataFrame(
        [[float(value) for value in row[1 : n_axes + 1]] for row in rows],
        index=[row[0] for row in rows],
        columns=[f"PC{i + 1}" for i in range(n_axes)],
    )
    coordinates.index.name = "sample"
    return coordinates, explained
