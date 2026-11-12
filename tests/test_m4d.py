import unittest


class ParseTacticsTests(unittest.TestCase):
    def test_parse_tactics_keeps_only_known_labels(self):
        from experiments.m4d_tactics.train import TACTICS, parse_tactics

        got = parse_tactics('["TA0001", "TA0002", "TA9999"]')
        self.assertEqual(got, ["TA0001", "TA0002"])
        self.assertEqual(TACTICS, ["TA0001", "TA0002", "TA0009", "TA0010", "TA0040"])

    def test_parse_tactics_empty_and_broken(self):
        from experiments.m4d_tactics.train import parse_tactics

        self.assertEqual(parse_tactics(""), [])
        self.assertEqual(parse_tactics("[]"), [])
        self.assertEqual(parse_tactics("no-json"), [])


if __name__ == "__main__":
    unittest.main()
