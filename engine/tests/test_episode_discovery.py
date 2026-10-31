import unittest
from rawsight.episode_discovery import discover_episodes


class EpisodeDiscoveryTests(unittest.TestCase):
    def run_discovery(self, rows, **options):
        return discover_episodes(rows, expected_interval_seconds=10, **options)

    def test_continuous_single_episode(self):
        result = self.run_discovery([
            {"time": "2020-01-01T00:00:00", "x": 1},
            {"time": "2020-01-01T00:00:10", "x": 2},
            {"time": "2020-01-01T00:00:20", "x": 3},
        ])
        self.assertEqual(result["episode_count"], 1)
        self.assertEqual(result["boundaries"], [])

    def test_gap_splits_and_identifies_reason(self):
        rows = [{"time": f"2020-01-01T00:00:{second:02d}", "x": 1} for second in (0, 10, 20, 50)]
        result = self.run_discovery(rows, gap_multiple=2.5)
        self.assertEqual(result["episode_count"], 2)
        self.assertEqual(result["boundaries"][0]["reason"], "temporal_gap")

    def test_concurrent_change_requires_multiple_signals(self):
        rows = [
            {"time": "2020-01-01T00:00:00", "x": 0, "y": 0},
            {"time": "2020-01-01T00:00:10", "x": 5, "y": 0},
            {"time": "2020-01-01T00:00:20", "x": 10, "y": 4},
        ]
        result = self.run_discovery(rows, change_thresholds={"x": 4, "y": 3})
        self.assertEqual(len(result["boundaries"]), 1)
        self.assertEqual(result["boundaries"][0]["signals"], ["x", "y"])

    def test_missing_values_do_not_create_changes(self):
        rows = [
            {"time": "2020-01-01T00:00:00", "x": 1, "y": None},
            {"time": "2020-01-01T00:00:10", "x": 100, "y": float("nan")},
        ]
        result = self.run_discovery(rows, change_thresholds={"x": 4, "y": 4})
        self.assertEqual(result["episode_count"], 1)
        self.assertEqual(result["episodes"][0]["valid_counts"]["y"], 0)

    def test_duplicates_rejected(self):
        rows = [{"time": "2020-01-01T00:00:00", "x": 1}] * 2
        with self.assertRaises(ValueError):
            self.run_discovery(rows)

    def test_deterministic_output(self):
        rows = [{"time": "2020-01-01T00:00:00", "x": 1}, {"time": "2020-01-01T00:00:10", "x": 2}]
        self.assertEqual(self.run_discovery(rows), self.run_discovery(rows))

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            self.run_discovery([], gap_multiple=1)
        with self.assertRaises(ValueError):
            self.run_discovery([], change_thresholds={"x": 0})


if __name__ == "__main__":
    unittest.main()
