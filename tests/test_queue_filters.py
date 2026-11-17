import unittest

import pandas as pd

from app.main import filter_queue_frame, paginate_frame


class QueueFilterTests(unittest.TestCase):
    def test_queue_filters_and_pagination_keep_filtered_total(self):
        events = pd.DataFrame(
            [
                {"artifact_id": "a", "timestamp": 10, "label_binary": "malicious", "org_id": "ORG-1", "message_type": "firewall_action", "severity": "warning", "src_ip": "10.0.0.1"},
                {"artifact_id": "b", "timestamp": 20, "label_binary": "malicious", "org_id": "ORG-2", "message_type": "firewall_action", "severity": "warning", "src_ip": "10.0.0.2"},
                {"artifact_id": "c", "timestamp": 30, "label_binary": "malicious", "org_id": "ORG-2", "message_type": "firewall_action", "severity": "warning", "src_ip": "10.0.0.3"},
                {"artifact_id": "d", "timestamp": 40, "label_binary": "suspicious", "org_id": "ORG-2", "message_type": "firewall_action", "severity": "warning", "src_ip": "10.0.0.4"},
                {"artifact_id": "e", "timestamp": 30.999, "label_binary": "malicious", "org_id": "ORG-2", "message_type": "firewall_action", "severity": "warning", "src_ip": "10.0.0.5"},
                {"artifact_id": "f", "timestamp": 31, "label_binary": "malicious", "org_id": "ORG-2", "message_type": "firewall_action", "severity": "warning", "src_ip": "10.0.0.6"},
            ]
        )

        filtered = filter_queue_frame(
            events,
            label="malicious",
            org_id="ORG-2",
            message_type="firewall_action",
            severity="warning",
            search="10.0.0.",
            start_ts=20,
            end_ts=31,
        )
        total, page = paginate_frame(filtered, offset=1, limit=1)

        self.assertEqual(total, 3)
        self.assertEqual(page["artifact_id"].tolist(), ["c"])


if __name__ == "__main__":
    unittest.main()
