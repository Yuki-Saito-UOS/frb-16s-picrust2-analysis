from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import kruskal, mannwhitneyu
from statsmodels.stats.multitest import multipletests


def clr_like_normalize(table: pd.DataFrame) -> pd.DataFrame:
    numeric = table.apply(pd.to_numeric, errors="coerce").fillna(0)
    rel = numeric.div(numeric.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    return np.log1p(rel * 1_000_000)


def summarize_groups(table: pd.DataFrame, groups: dict[str, list[str]]) -> pd.DataFrame:
    rows = []
    for sample in table.index:
        group = next((g for g, names in groups.items() if sample in names), None)
        if group is not None:
            rows.append({"sample": sample, "group": group})
    return pd.DataFrame(rows)


def _add_q_values(result: pd.DataFrame) -> pd.DataFrame:
    if result.empty:
        return result

    valid = result["p_value"].notna()
    result["q_value"] = np.nan
    if valid.any():
        result.loc[valid, "q_value"] = multipletests(result.loc[valid, "p_value"], method="fdr_bh")[1]
    return result


def _effect_col(group_a: str, group_b: str) -> str:
    return f"effect_{group_b}_vs_{group_a}"


def kruskal_by_feature(table: pd.DataFrame, groups: dict[str, list[str]], feature_col: str) -> pd.DataFrame:
    return compare_three_groups(table, groups, feature_col)


def compare_three_groups(table: pd.DataFrame, groups: dict[str, list[str]], feature_col: str) -> pd.DataFrame:
    table = clr_like_normalize(table)
    rows = []
    group_names = list(groups)

    for feature in table.columns:
        values_by_group = []
        means = {}
        for group in group_names:
            samples = [s for s in groups[group] if s in table.index]
            values = table.loc[samples, feature].dropna()
            values_by_group.append(values)
            means[f"{group}_mean"] = float(values.mean()) if len(values) else np.nan

        if sum(len(v) > 0 for v in values_by_group) < 2:
            p_value = np.nan
        else:
            try:
                p_value = float(kruskal(*values_by_group, nan_policy="omit").pvalue)
            except ValueError:
                p_value = np.nan

        row = {feature_col: feature, "p_value": p_value, **means}
        row["max_mean_group"] = max(
            group_names,
            key=lambda g: -np.inf if pd.isna(row[f"{g}_mean"]) else row[f"{g}_mean"],
        )

        for index, group_a in enumerate(group_names):
            for group_b in group_names[index + 1 :]:
                row[_effect_col(group_a, group_b)] = row[f"{group_b}_mean"] - row[f"{group_a}_mean"]

        rows.append(row)

    result = pd.DataFrame(rows)
    result = _add_q_values(result)
    return result.sort_values(["p_value", feature_col], na_position="last")


def compare_two_groups(
    table: pd.DataFrame,
    groups: dict[str, list[str]],
    feature_col: str,
    group_a: str,
    group_b: str,
) -> pd.DataFrame:
    table = clr_like_normalize(table)
    rows = []

    samples_a = [s for s in groups[group_a] if s in table.index]
    samples_b = [s for s in groups[group_b] if s in table.index]

    for feature in table.columns:
        values_a = table.loc[samples_a, feature].dropna()
        values_b = table.loc[samples_b, feature].dropna()

        if len(values_a) == 0 or len(values_b) == 0:
            p_value = np.nan
        else:
            try:
                p_value = float(mannwhitneyu(values_a, values_b, alternative="two-sided").pvalue)
            except ValueError:
                p_value = np.nan

        mean_a = float(values_a.mean()) if len(values_a) else np.nan
        mean_b = float(values_b.mean()) if len(values_b) else np.nan
        row = {
            feature_col: feature,
            "comparison": f"{group_a}_vs_{group_b}",
            "p_value": p_value,
            f"{group_a}_mean": mean_a,
            f"{group_b}_mean": mean_b,
            _effect_col(group_a, group_b): mean_b - mean_a,
        }
        row["max_mean_group"] = group_b if mean_b > mean_a else group_a
        rows.append(row)

    result = pd.DataFrame(rows)
    result = _add_q_values(result)
    return result.sort_values(["p_value", feature_col], na_position="last")


def select_top_features(df: pd.DataFrame, feature_col: str, p_value: float, effect: float, top_n: int) -> pd.DataFrame:
    df = df.copy()
    effect_cols = [c for c in df.columns if c.startswith("effect_")]
    if effect_cols:
        df["max_abs_effect"] = df[effect_cols].abs().max(axis=1)
        df = df[df["max_abs_effect"] >= effect]
    df = df[df["p_value"] <= p_value]
    return df.sort_values(["p_value", "max_abs_effect" if "max_abs_effect" in df.columns else feature_col]).head(top_n)
