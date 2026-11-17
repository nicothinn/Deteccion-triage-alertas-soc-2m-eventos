import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

import app.main as api
from app.main import FeedbackIn


class FeedbackTests(unittest.TestCase):
    def test_rejects_unknown_decision(self):
        with self.assertRaises(ValidationError):
            FeedbackIn(decision="ignore_everything")

    def test_feedback_csv_keeps_quotes_commas_and_counts_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "data").mkdir()
            note = 'quoted, value "here"\nsecond line'
            with patch.object(api, "ROOT", Path(tmp)):
                result = api.feedback(FeedbackIn(
                    artifact_id="artifact-1", decision="falso_positivo", note=note
                ))

            with (Path(tmp) / "data" / "feedback.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.reader(handle))

        self.assertEqual(result["n"], 1)
        self.assertEqual(rows[1][1:], ["artifact-1", "falso_positivo", 'quoted, value "here" second line'])

    def test_feedback_uses_configured_persistent_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            persistent = Path(tmp) / "volume" / "feedback.csv"
            persistent.parent.mkdir()
            with patch.dict(os.environ, {"FEEDBACK_PATH": str(persistent)}), patch.object(api, "ROOT", Path(tmp)):
                api.feedback(FeedbackIn(artifact_id="a", decision="monitorear"))

            self.assertTrue(persistent.exists())
            self.assertFalse((Path(tmp) / "data" / "feedback.csv").exists())


if __name__ == "__main__":
    unittest.main()
