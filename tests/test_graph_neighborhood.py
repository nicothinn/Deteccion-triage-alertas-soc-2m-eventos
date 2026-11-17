import unittest

import pandas as pd

from app.main import graph_neighborhood


class GraphNeighborhoodTests(unittest.TestCase):
    def test_two_hops_are_bounded_and_do_not_revisit_cycles(self):
        edges = pd.DataFrame(
            [
                {"src": "A", "dst": "B", "type": "USER_ACTION"},
                {"src": "A", "dst": "Z", "type": "NETWORK_FLOW"},
                {"src": "B", "dst": "C", "type": "NETWORK_FLOW"},
                {"src": "B", "dst": "D", "type": "NETWORK_FLOW"},
                {"src": "C", "dst": "A", "type": "USER_ACTION"},
                {"src": "Z", "dst": "E", "type": "DNS_RESOLVE"},
            ]
        )

        selected, depths = graph_neighborhood(edges, "A", depth=2, limit=2, types=None)

        self.assertEqual(depths, {"A": 0, "B": 1, "Z": 1, "C": 2, "D": 2})
        self.assertEqual(len(selected), 4)
        self.assertEqual(selected["depth"].tolist(), [1, 1, 2, 2])

    def test_edge_type_filter_applies_to_each_hop(self):
        edges = pd.DataFrame(
            [
                {"src": "A", "dst": "B", "type": "USER_ACTION"},
                {"src": "B", "dst": "C", "type": "NETWORK_FLOW"},
                {"src": "B", "dst": "D", "type": "AUDIT_EVENT"},
            ]
        )

        selected, depths = graph_neighborhood(edges, "A", depth=2, limit=5, types={"USER_ACTION"})

        self.assertEqual(depths, {"A": 0, "B": 1})
        self.assertEqual(selected["type"].tolist(), ["USER_ACTION"])


if __name__ == "__main__":
    unittest.main()
