import unittest

import duckdb

from rawsight.cross_series_presence import (
    analyze_cross_series_presence,
)


class TestCrossSeriesPresence(unittest.TestCase):

    def setUp(self):
        self.connection = duckdb.connect(":memory:")

        self.connection.execute("""
            CREATE TABLE measurements (
                time TIMESTAMP,
                sensor_a DOUBLE,
                sensor_b DOUBLE
            )
        """)

        self.connection.execute("""
            INSERT INTO measurements VALUES
            ('2020-04-25 10:00:00', 1.0, NULL),
            ('2020-04-25 10:01:00', NULL, 4.0),
            ('2020-04-25 10:02:00', 3.0, 'Infinity'::DOUBLE),
            ('2020-04-26 10:00:00', 9.0, 8.0),
            (NULL, 5.0, 5.0)
        """)

        class Context:
            view_name = "measurements"
            column_names = [
                "time", "sensor_a", "sensor_b"
            ]
            column_types = [
                "TIMESTAMP", "DOUBLE", "DOUBLE"
            ]

            def __init__(self, connection):
                self.connection = connection

            def require_connection(self):
                return self.connection

        self.context = Context(self.connection)
        self.axis = {
            "orientation": "vertical",
            "sequence_index": 0,
        }

    def tearDown(self):
        self.connection.close()

    def analyze(self, start, end):
        return analyze_cross_series_presence(
            self.context,
            self.axis,
            start,
            end,
        )

    def test_counts_and_extrema(self):
        result = self.analyze(
            "2020-04-25 10:00:00",
            "2020-04-25 10:02:00",
        )

        self.assertEqual(result["source_row_count"], 3)
        self.assertEqual(result["numeric_column_count"], 2)

        a, b = result["columns"]

        self.assertEqual(
            (a["valid_count"], a["missing_count"],
             a["invalid_count"]), (2, 1, 0)
        )
        self.assertEqual(
            (a["minimum"], a["maximum"]), (1.0, 3.0)
        )

        self.assertEqual(
            (b["valid_count"], b["missing_count"],
             b["invalid_count"]), (1, 1, 1)
        )
        self.assertEqual(
            (b["minimum"], b["maximum"]), (4.0, 4.0)
        )

    def test_empty_interval(self):
        result = self.analyze(
            "2020-05-01",
            "2020-05-02",
        )
        self.assertEqual(result["source_row_count"], 0)
        self.assertEqual(result["status"], "insufficient_data")

    def test_invalid_range(self):
        with self.assertRaises(ValueError):
            self.analyze(
                "2020-05-02",
                "2020-05-01",
            )

    def test_outside_rows_excluded(self):
        result = self.analyze(
            "2020-04-25",
            "2020-04-25 23:59:59",
        )
        self.assertEqual(result["source_row_count"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)