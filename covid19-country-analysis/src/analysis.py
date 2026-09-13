"""Core transformations and validation for the country-level COVID-19 analysis."""

from __future__ import annotations

import pandas as pd


REQUIRED_COLUMNS = {
    "Country/Region",
    "WHO Region",
    "Confirmed",
    "Deaths",
    "Recovered",
    "Active",
    "New cases",
    "New deaths",
    "New recovered",
    "Confirmed last week",
    "1 week change",
    "1 week % increase",
}


def validate_data(data: pd.DataFrame) -> dict[str, int]:
    """Validate schema, uniqueness, missingness, and the case-count identity."""
    missing_columns = REQUIRED_COLUMNS.difference(data.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    duplicate_countries = int(data["Country/Region"].duplicated().sum())
    missing_values = int(data.isna().sum().sum())
    identity_failures = int(
        (
            data["Confirmed"]
            != data["Deaths"] + data["Recovered"] + data["Active"]
        ).sum()
    )

    return {
        "rows": len(data),
        "columns": len(data.columns),
        "missing_values": missing_values,
        "duplicate_countries": duplicate_countries,
        "case_identity_failures": identity_failures,
    }


def build_regional_summary(data: pd.DataFrame) -> pd.DataFrame:
    """Aggregate country observations and calculate weighted regional rates."""
    summary = (
        data.groupby("WHO Region", as_index=False)
        .agg(
            countries=("Country/Region", "nunique"),
            confirmed=("Confirmed", "sum"),
            deaths=("Deaths", "sum"),
            recovered=("Recovered", "sum"),
            active=("Active", "sum"),
            new_cases=("New cases", "sum"),
            confirmed_last_week=("Confirmed last week", "sum"),
            one_week_change=("1 week change", "sum"),
        )
    )

    total_confirmed = summary["confirmed"].sum()
    summary = summary.assign(
        case_share_pct=summary["confirmed"].div(total_confirmed).mul(100),
        fatality_pct=summary["deaths"].div(summary["confirmed"]).mul(100),
        recovery_pct=summary["recovered"].div(summary["confirmed"]).mul(100),
        active_pct=summary["active"].div(summary["confirmed"]).mul(100),
        weekly_growth_pct=summary["one_week_change"]
        .div(summary["confirmed_last_week"])
        .mul(100),
    )
    return summary.sort_values("confirmed", ascending=False).reset_index(drop=True)


def build_global_summary(data: pd.DataFrame) -> pd.Series:
    """Return headline totals and weighted rates for the full snapshot."""
    confirmed = data["Confirmed"].sum()
    return pd.Series(
        {
            "Countries": data["Country/Region"].nunique(),
            "Confirmed cases": confirmed,
            "Deaths": data["Deaths"].sum(),
            "Recovered": data["Recovered"].sum(),
            "Active cases": data["Active"].sum(),
            "One-week growth rate (%)": data["1 week change"].sum()
            / data["Confirmed last week"].sum()
            * 100,
            "Case fatality rate (%)": data["Deaths"].sum() / confirmed * 100,
        }
    )


def rank_countries(
    data: pd.DataFrame,
    metric: str,
    n: int = 10,
    minimum_confirmed: int = 0,
) -> pd.DataFrame:
    """Return the highest-ranked countries for a metric after a volume filter."""
    if metric not in data.columns:
        raise ValueError(f"Unknown metric: {metric}")
    eligible = data.loc[data["Confirmed"] >= minimum_confirmed]
    columns = list(dict.fromkeys(["Country/Region", "WHO Region", "Confirmed", metric]))
    return eligible.nlargest(n, metric)[columns].reset_index(drop=True)
