"""Tests for the reusable COVID-19 analysis transformations."""

import unittest
from pathlib import Path

import pandas as pd

from src.analysis import (
    build_global_summary,
    build_regional_summary,
    rank_countries,
    validate_data,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "country_wise_latest.csv"


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = pd.read_csv(DATA_PATH)

    def test_source_data_passes_quality_checks(self) -> None:
        audit = validate_data(self.data)
        self.assertEqual(audit["rows"], 187)
        self.assertEqual(audit["missing_values"], 0)
        self.assertEqual(audit["duplicate_countries"], 0)
        self.assertEqual(audit["case_identity_failures"], 0)

    def test_regional_totals_reconcile_to_source(self) -> None:
        regional = build_regional_summary(self.data)
        self.assertEqual(regional["confirmed"].sum(), self.data["Confirmed"].sum())
        self.assertAlmostEqual(regional["case_share_pct"].sum(), 100.0)

    def test_global_summary_uses_weighted_rates(self) -> None:
        summary = build_global_summary(self.data)
        expected = self.data["Deaths"].sum() / self.data["Confirmed"].sum() * 100
        self.assertAlmostEqual(summary["Case fatality rate (%)"], expected)

    def test_growth_ranking_applies_volume_filter(self) -> None:
        ranked = rank_countries(
            self.data, "1 week % increase", n=10, minimum_confirmed=1_000
        )
        self.assertTrue((ranked["Confirmed"] >= 1_000).all())
        self.assertTrue(ranked["1 week % increase"].is_monotonic_decreasing)

    def test_confirmed_ranking_has_unique_columns(self) -> None:
        ranked = rank_countries(self.data, "Confirmed")
        self.assertEqual(len(ranked.columns), len(set(ranked.columns)))


if __name__ == "__main__":
    unittest.main()
