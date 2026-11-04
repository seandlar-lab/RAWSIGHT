"""Quality region execution unit tests + DuckDB integration tests."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from rawsight.quality_region_execution import _check_inputs, _identifier


class ValidationTests(unittest.TestCase):
    def test_quoted_identifier(self):
        self.assertEqual(_identifier('a"b'), '"a""b"')

    def test_default_columns(self):
        self.assertEqual(_check_inputs(['a', 'b'], time_column=None, columns=None, max_rows=10), ['a', 'b'])

    def test_unknown_time_column(self):
        with self.assertRaises(ValueError):
            _check_inputs(['x'], time_column='t', columns=None, max_rows=10)

    def test_duplicate_columns(self):
        with self.assertRaises(ValueError):
            _check_inputs(['a', 'b'], time_column=None, columns=['a', 'a'], max_rows=10)

    def test_cap_is_bounded(self):
        with self.assertRaises(ValueError):
            _check_inputs(['x'], time_column=None, columns=None, max_rows=100001)

    def test_no_implicit_subset(self):
        with self.assertRaises(ValueError):
            _check_inputs([f'c{i}' for i in range(25)], time_column=None, columns=None, max_rows=10)


try:
    import duckdb  # noqa
except ImportError:
    duckdb = None


@unittest.skipIf(duckdb is None, 'DuckDB not installed in test environment')
class SourceIntegrationTests(unittest.TestCase):
    def make_csv(self, folder, rows):
        p = Path(folder) / 'quality_source.csv'
        p.write_text('t,x,y\n' + '\n'.join(rows) + '\n', encoding='utf-8')
        return str(p)

    def test_exact_whole_and_repeated_timestamps(self):
        from rawsight.quality_region_execution import execute_quality_regions
        with tempfile.TemporaryDirectory() as td:
            src = self.make_csv(td, ['2020-01-01 00:00:00,1,ok',
                                     '2020-01-01 01:00:00,,ok',
                                     '2020-01-01 01:00:00,3,ok',
                                     '2020-01-01 03:00:00,4,ok'])
            r = execute_quality_regions(file_path=src, time_column='t', columns=['x', 'y'], max_rows=10)
            self.assertEqual(r['status'], 'complete')
            self.assertEqual(r['whole_source_quality']['row_count'], 4)
            self.assertEqual(r['whole_source_quality']['temporal']['extra_rows_beyond_unique_timestamps'], 1)
            self.assertEqual(r['whole_source_quality']['missing_by_column']['x'], 1)
            self.assertEqual(r['region_coverage']['rows_evaluated'], 4)

    def test_bounded_preview_is_explicitly_partial(self):
        from rawsight.quality_region_execution import execute_quality_regions
        with tempfile.TemporaryDirectory() as td:
            src = self.make_csv(td, [f'2020-01-01 0{i}:00:00,{i},ok' for i in range(6)])
            r = execute_quality_regions(file_path=src, time_column='t', columns=['x'], max_rows=3)
            self.assertEqual(r['status'], 'partial_region_coverage')
            self.assertEqual(r['whole_source_quality']['row_count'], 6)
            self.assertEqual(r['region_coverage']['rows_evaluated'], 3)
            self.assertFalse(r['region_coverage']['exhaustive'])

    def test_non_temporal(self):
        from rawsight.quality_region_execution import execute_quality_regions
        with tempfile.TemporaryDirectory() as td:
            src = self.make_csv(td, ['2020-01-01 00:00:00,1,good',
                                     '2020-01-02 00:00:00,,bad'])
            r = execute_quality_regions(file_path=src, columns=['x', 'y'], max_rows=10)
            self.assertIsNone(r['whole_source_quality']['temporal'])
            self.assertEqual(r['whole_source_quality']['missing_by_column']['x'], 1)

    def test_original_csv_unchanged(self):
        from rawsight.quality_region_execution import execute_quality_regions
        with tempfile.TemporaryDirectory() as td:
            src = self.make_csv(td, ['2020-01-01 00:00:00,1,ok', '2020-01-01 01:00:00,2,ok'])
            before = Path(src).read_bytes()
            execute_quality_regions(file_path=src, time_column='t', max_rows=10)
            self.assertEqual(Path(src).read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
