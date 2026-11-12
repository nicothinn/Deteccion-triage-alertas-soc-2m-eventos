import unittest


class TuneThresholdTests(unittest.TestCase):
    def test_pick_threshold_maximizes_fbeta_on_validation(self):
        import numpy as np
        from experiments.m4t_thresholds.train import pick_threshold

        y = np.array([0, 0, 0, 1, 1, 1, 1])
        s = np.array([0.1, 0.2, 0.35, 0.4, 0.6, 0.8, 0.9])
        thr, f2 = pick_threshold(y, s, beta=2.0)
        self.assertGreaterEqual(thr, 0.35)
        self.assertLessEqual(thr, 0.45)
        self.assertGreater(f2, 0.9)

    def test_pick_threshold_without_positives_returns_default(self):
        import numpy as np
        from experiments.m4t_thresholds.train import pick_threshold

        thr, f2 = pick_threshold(np.zeros(10), np.linspace(0, 1, 10))
        self.assertEqual(thr, 0.5)
        self.assertEqual(f2, 0.0)


if __name__ == "__main__":
    unittest.main()
