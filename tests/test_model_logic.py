import unittest

import numpy as np
import pandas as pd


class CausalGraphFeatureTests(unittest.TestCase):
    def test_graph_neighbors_are_strictly_in_the_past_and_within_300_seconds(self):
        from experiments.m3_grafo.train import graph_feats

        full = pd.DataFrame(
            {
                "timestamp": [900.0, 1000.0, 1000.0, 1001.0, 699.0],
                "org_id": ["o"] * 5,
                "message_type": ["firewall_action"] * 5,
                "action": ["block"] * 5,
                "src_ip": ["host"] * 5,
                "dst_ip": [""] * 5,
                "username": [""] * 5,
            }
        )

        features = graph_feats(full, np.array([2]))

        self.assertEqual(float(features.iloc[0]["n_neigh"]), 1.0)


class ScoreFusionTests(unittest.TestCase):
    def test_m2_malicious_overrides_m1_tier(self):
        import app.main as api

        fuse = getattr(api, "fuse_prediction", None)
        self.assertIsNotNone(fuse, "score fusion helper is missing")
        self.assertEqual(fuse("benign", "malicious", "allow"), ("malicious", "escalar"))

    def test_suspicious_block_escalates_but_keeps_model_tier(self):
        import app.main as api

        fuse = getattr(api, "fuse_prediction", None)
        self.assertIsNotNone(fuse, "score fusion helper is missing")
        self.assertEqual(fuse("suspicious", None, "block"), ("suspicious", "escalar"))

    def test_suspicious_non_block_is_monitored(self):
        import app.main as api

        fuse = getattr(api, "fuse_prediction", None)
        self.assertIsNotNone(fuse, "score fusion helper is missing")
        self.assertEqual(fuse("suspicious", None, "allow"), ("suspicious", "monitorear"))


if __name__ == "__main__":
    unittest.main()
