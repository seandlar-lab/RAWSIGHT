"""Tests for the DuckDB source adapter using a deterministic fake source session."""
import unittest
from datetime import datetime, timedelta
from rawsight.episode_discovery_execution import execute_episode_discovery


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.last_sql = None
        self.last_args = None

    def execute(self, sql, arguments):
        self.last_sql = sql
        self.last_args = arguments
        return self

    def fetchall(self):
        return self.rows[:self.last_args[-1]]


class FakeContext:
    is_open = True
    view_name = "rawsight_source"
    column_names = ["time", "a", "b", "label"]
    column_types = ["TIMESTAMP", "DOUBLE", "INTEGER", "VARCHAR"]

    def __init__(self, rows):
        self.connection = FakeConnection(rows)

    def assert_source(self, file_path):
        assert file_path == "synthetic.csv"

    def require_connection(self):
        return self.connection


AXIS = {"orientation": "vertical", "sequence_index": 0}
BASE = dict(file_path="synthetic.csv", temporal_axis=AXIS,
            start_time="2020-01-01T00:00:00", end_time="2020-01-01T00:02:00",
            expected_interval_seconds=10)


def rows(*seconds):
    start = datetime(2020, 1, 1)
    return [(start + timedelta(seconds=s), float(s), int(s)) for s in seconds]


class EpisodeDiscoveryExecutionTests(unittest.TestCase):
    def test_gap_through_existing_source_context(self):
        context = FakeContext(rows(0, 10, 20, 100, 110, 120))
        result = execute_episode_discovery(**BASE, source_context=context)
        self.assertEqual(result["status"], "measured")
        self.assertEqual(result["episode_count"], 2)
        self.assertEqual(result["boundaries"][0]["gap_seconds"], 80)
        self.assertEqual(result["columns_considered"], ["a", "b"])
        self.assertIn("TRY_CAST", context.connection.last_sql)

    def test_excessive_interval_not_partially_classified(self):
        result = execute_episode_discovery(**BASE, source_context=FakeContext(rows(0, 10, 20, 30)), max_observations=3)
        self.assertEqual(result["status"], "resource_limit")
        self.assertEqual(result["episodes"], [])
        self.assertEqual(result["boundaries"], [])

    def test_select_only_numeric_columns(self):
        with self.assertRaises(ValueError):
            execute_episode_discovery(**BASE, source_context=FakeContext([]), selected_columns=["label"])

    def test_duplicate_timestamps_rejected(self):
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            execute_episode_discovery(**BASE, source_context=FakeContext(rows(0, 0)))

    def test_invalid_window_rejected(self):
        with self.assertRaises(ValueError):
            execute_episode_discovery(**{**BASE, "end_time": BASE["start_time"]}, source_context=FakeContext([]))

    def test_empty_selection_is_insufficient_data(self):
        result = execute_episode_discovery(**BASE, source_context=FakeContext([]))
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["episode_count"], 0)

    def test_explicit_threshold_creates_multisignal_boundary(self):
        result = execute_episode_discovery(**BASE, source_context=FakeContext(rows(0, 10, 20)), change_thresholds={"a": 5, "b": 5})
        self.assertEqual(result["boundaries"][0]["reason"], "concurrent_change")


if __name__ == "__main__":
    unittest.main()
