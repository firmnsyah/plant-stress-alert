"""Statistical summaries used by the analysis page."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
from scipy import stats
from sklearn.decomposition import PCA


def anova_tukey(df: pd.DataFrame, value_col: str, group_col: str = "treatment") -> dict[str, object]:
    groups = [group[value_col].dropna().to_numpy() for _, group in df.groupby(group_col)]
    groups = [group for group in groups if len(group)]
    if len(groups) < 2:
        raise ValueError("ANOVA membutuhkan minimal dua kelompok dengan data.")
    statistic, p_value = stats.f_oneway(*groups)
    tukey = None
    if len(df[group_col].dropna().unique()) > 1:
        from statsmodels.stats.multicomp import pairwise_tukeyhsd

        tukey = pairwise_tukeyhsd(df[value_col], df[group_col]).summary()
    return {"f_statistic": float(statistic), "p_value": float(p_value), "tukey": tukey}


def pca(df: pd.DataFrame, columns: Iterable[str]) -> dict[str, object]:
    values = df[list(columns)].astype(float).to_numpy()
    if len(values) < 2:
        raise ValueError("PCA membutuhkan minimal dua observasi.")
    model = PCA(n_components=min(2, values.shape[1]))
    scores = model.fit_transform(values)
    return {"scores": scores, "explained_variance_ratio": model.explained_variance_ratio_}


def first_significant_day(df: pd.DataFrame, value_col: str, day_col: str = "day_after_treatment") -> int | None:
    control = df[df["treatment"] == "kontrol"]
    for day in sorted(df[day_col].dropna().unique()):
        current = df[df[day_col] == day]
        treatment = current[current["treatment"] != "kontrol"][value_col].dropna()
        baseline = control[control[day_col] == day][value_col].dropna()
        if len(treatment) >= 2 and len(baseline) >= 2 and stats.ttest_ind(treatment, baseline, equal_var=False).pvalue < 0.05:
            return int(day)
    return None
