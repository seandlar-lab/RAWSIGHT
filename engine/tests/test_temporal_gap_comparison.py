import unittest

import duckdb

from rawsight.temporal_gap_comparison import (
    analyze_temporal_gap_comparison,
)


class FakeContext:
    view_name = "measurements"
    column_names = [
        "timestamp",
        "TP3",
        "Oil_temperature",
    ]
    column_types = [
        "TIMESTAMP",
        "DOUBLE",
        "DOUBLE",
    ]

    def __init__(self, connection):
        self.connection = connection

    def require_connection(self):
        return self.connection


class TemporalGapComparisonTests(unittest.TestCase):

    def setUp(self):
        self.connection = duckdb.connect(":memory:")

        self.connection.execute("""
            CREATE TABLE measurements (
                timestamp TIMESTAMP,
                TP3 DOUBLE,
                Oil_temperature DOUBLE
            )
        """)

        self.connection.executemany(
            "INSERT INTO measurements VALUES (?, ?, ?)",
            [
                ("2020-04-17 00:00:00", 10.0, 30.0),
                ("2020-04-17 00:01:00", 12.0, 32.0),
                ("2020-04-17 00:02:00", 14.0, None),
                ("2020-04-17 00:10:00", 20.0, 40.0),
                ("2020-04-17 00:11:00", 22.0, 42.0),
                ("2020-04-17 00:12:00", 24.0, 44.0),
            ],
        )

        self.context = FakeContext(self.connection)

        self.axis = {
            "orientation": "vertical",
            "sequence_index": 0,
        }

    def tearDown(self):
        self.connection.close()

    def analyze(self, **overrides):
        arguments = {
            "source_context": self.context,
            "temporal_axis": self.axis,
            "gap_start": "2020-04-17 00:02:00",
            "gap_end": "2020-04-17 00:10:00",
            "observations_per_side": 2,
        }
        arguments.update(overrides)

        return analyze_temporal_gap_comparison(
            **arguments
        )

    def test_mean_delta(self):
        result = self.analyze()

        tp3 = next(
            c for c in result["columns"]
            if c["column_name"] == "TP3"
        )

        self.assertEqual(result["status"], "measured")
        self.assertEqual(result["before_observation_count"], 2)
        self.assertEqual(result["after_observation_count"], 2)
        self.assertEqual(tp3["before"]["mean"], 13.0)
        self.assertEqual(tp3["after"]["mean"], 21.0)
        self.assertEqual(tp3["mean_delta"], 8.0)

    def test_missing_values(self):
        result = self.analyze()

        oil = next(
            c for c in result["columns"]
            if c["column_name"] == "Oil_temperature"
        )

        self.assertEqual(oil["before"]["valid_count"], 1)
        self.assertEqual(oil["after"]["valid_count"], 2)

    def test_invalid_interval(self):
        with self.assertRaises(ValueError):
            self.analyze(
                gap_start="2020-04-17 00:10:00",
                gap_end="2020-04-17 00:02:00",
            )

    def test_missing_after_window(self):
        result = self.analyze(
            gap_start="2021-01-01",
            gap_end="2021-01-02",
        )

        self.assertEqual(
            result["status"],
            "insufficient_data",
        )
        self.assertEqual(
            result["after_observation_count"],
            0,
        )


if __name__ == "__main__":
    unittest.main()