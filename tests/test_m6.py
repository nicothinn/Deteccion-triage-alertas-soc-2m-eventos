import unittest


class BuildIncidentsTests(unittest.TestCase):
    def test_build_incidents_aggregates_signals_and_votes_labels(self):
        import pandas as pd
        from experiments.m6_incident.train import TECHS, build_incidents

        df = pd.DataFrame({
            "timestamp": [1000.0, 1060.0, 2000.0],
            "message_type": ["a", "b", "a"],
            "action": ["allow", "block", "allow"],
            "attack_techniques": ['["T1190"]', '["T1190", "T1041"]', '["T1041"]'],
            "org_id": ["ORG-1", "ORG-1", "ORG-2"],
            "src_ip": ["h1", "h2", "h9"],
            "dst_ip": ["", "", ""],
            "username": ["u1", "u1", "u2"],
            "iid": ["i1", "i1", "i2"],
        })
        inc, Y = build_incidents(df)
        self.assertEqual(list(inc["iid"]), ["i1", "i2"])
        self.assertEqual(TECHS, ["T1190", "T1041", "T1567", "T1204", "T1486", "T1566"])
        row = inc.set_index("iid").loc["i1"]
        self.assertEqual(int(row["n_signals"]), 2)
        self.assertAlmostEqual(float(row["frac_block"]), 0.5)
        self.assertEqual(Y[0].tolist(), [1, 1, 0, 0, 0, 0])
        self.assertEqual(Y[1].tolist(), [0, 1, 0, 0, 0, 0])

    def test_incident_vote_takes_max_over_signals(self):
        import numpy as np
        import pandas as pd
        from experiments.m6_incident.train import incident_vote

        proba = pd.DataFrame(
            {"iid": ["i1", "i1", "i2"], "T1190": [0.2, 0.8, 0.1], "T1041": [0.9, 0.1, 0.4]}
        )
        out = incident_vote(proba, ["T1190", "T1041"])
        self.assertEqual(list(out["iid"]), ["i1", "i2"])
        self.assertAlmostEqual(float(out.set_index("iid").loc["i1", "T1190"]), 0.8)
        self.assertAlmostEqual(float(out.set_index("iid").loc["i1", "T1041"]), 0.9)


if __name__ == "__main__":
    unittest.main()
