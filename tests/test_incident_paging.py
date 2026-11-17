import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import app.main as api
from app.main import incident_page_frame


class IncidentPagingTests(unittest.TestCase):
    def test_incident_page_is_time_ordered_and_keeps_total(self):
        events = pd.DataFrame(
            [
                {"artifact_id": "c", "timestamp": 30, "incident_ids": '["inc-1"]'},
                {"artifact_id": "a", "timestamp": 10, "incident_ids": '["inc-1"]'},
                {"artifact_id": "other", "timestamp": 15, "incident_ids": '["inc-10"]'},
                {"artifact_id": "b", "timestamp": 20, "incident_ids": '["inc-1"]'},
            ]
        )

        total, page = incident_page_frame(events, "inc-1", offset=1, limit=1)

        self.assertEqual(total, 3)
        self.assertEqual(page["artifact_id"].tolist(), ["b"])

    def test_incident_endpoint_preserves_existing_event_fields(self):
        events = pd.DataFrame(
            [{"artifact_id": "a", "timestamp": 10, "incident_ids": '["inc-1"]',
              "message_type": "firewall_action", "action": "block", "label_binary": "malicious",
              "src_ip": "192.0.2.1", "severity": "warning", "org_id": "ORG-1"}]
        )

        def read_parquet(_path, columns=None):
            return events[columns] if columns else events.copy()

        with patch.object(api.pd, "read_parquet", side_effect=read_parquet), patch.object(api, "REP", Path("missing-test-report.parquet")):
            result = api.incident("inc-1", limit=30, offset=0)

        self.assertEqual(result["events"][0]["severity"], "warning")
        self.assertEqual(result["events"][0]["org_id"], "ORG-1")


if __name__ == "__main__":
    unittest.main()
