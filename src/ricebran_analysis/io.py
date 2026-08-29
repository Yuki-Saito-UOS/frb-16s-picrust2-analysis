from __future__ import annotations

from pathlib import Path
import re

import pandas as pd


def sample_to_group(sample: str, groups: dict[str, list[str]]) -> str | None:
    sample = str(sample)
    for group, samples in groups.items():
        if sample in samples or any(sample.startswith(prefix) for prefix in samples):
            return group
    return None


def clean_taxon_name(value: object, rank: str = "g") -> str:
    if pd.isna(value):
        return "Unassigned"

    text = str(value)
    for part in text.split(";"):
        part = part.strip()
        marker = f"{rank}__"
        if part.startswith(marker):
            name = part.replace(marker, "").strip()
            return name or "Unassigned"
    return "Unassigned"


def read_genus_table(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t", skiprows=1)
    feature_col = df.columns[0]
    df = df.rename(columns={feature_col: "taxon"})
    df["genus"] = df["taxon"].map(clean_taxon_name)

    sample_cols = [c for c in df.columns if c not in {"taxon", "genus"} and "tax" not in c.lower()]
    values = df[["genus", *sample_cols]].groupby("genus", as_index=True).sum(numeric_only=True)
    return values.T.rename_axis("sample")


def read_feature_table(path: Path, feature_name: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t")
    first = df.columns[0]
    df = df.rename(columns={first: feature_name})
    df[feature_name] = df[feature_name].astype(str)

    sample_cols = [c for c in df.columns if c != feature_name and re.search(r"\d$", str(c))]
    values = df[[feature_name, *sample_cols]].set_index(feature_name)
    return values.T.rename_axis("sample")
