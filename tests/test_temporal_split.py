from datetime import datetime, timezone
import unittest

import pandas as pd


def epoch(value: str) -> float:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()


class TemporalSplitTests(unittest.TestCase):
    def test_temporal_windows_preserve_rows_and_use_shared_utc_boundaries(self):
        try:
            from src.temporal_split import temporal_windows
        except ImportError:
            temporal_windows = None
        self.assertIsNotNone(temporal_windows, "shared temporal split helper is missing")

        rows = pd.DataFrame(
            {
                "artifact_id": list("abcdef"),
                "timestamp": [
                    epoch("2024-07-28T23:59:59"),
                    epoch("2024-07-29T00:00:00"),
                    epoch("2024-07-30T23:59:59"),
                    epoch("2024-07-31T00:00:00"),
                    epoch("2024-08-01T23:59:59"),
                    epoch("2024-08-02T00:00:00"),
                ],
            }
        )

        train, test, drift = temporal_windows(rows)

        self.assertEqual(train["artifact_id"].tolist(), ["a"])
        self.assertEqual(test["artifact_id"].tolist(), ["b", "c"])
        self.assertEqual(drift["artifact_id"].tolist(), ["d", "e"])
        self.assertEqual(
            len(train) + len(test) + len(drift),
            len(rows) - 1,
            "the row at the exclusive end boundary must not enter any window",
        )

    def test_population_summary_keeps_natural_test_counts_and_prevalence(self):
        try:
            from src.temporal_split import population_summary
        except ImportError:
            population_summary = None
        self.assertIsNotNone(population_summary, "test population summary is missing")

        summary = population_summary(
            pd.DataFrame({"label_binary": ["benign"] * 3 + ["suspicious"] * 2 + ["malicious"]})
        )

        self.assertEqual(summary["n"], 6)
        self.assertEqual(summary["class_counts"], {"benign": 3, "suspicious": 2, "malicious": 1})
        self.assertEqual(summary["prevalence"], {"benign": 0.5, "suspicious": 0.333333, "malicious": 0.166667})


if __name__ == "__main__":
    unittest.main()
