"""Tests for full-source streaming quality execution v0.2."""
import json
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest

from rawsight.quality_region_execution_v2 import (
    _boundaries, _region_findings, _spans, _validate,
)


class StreamingContractTests(unittest.TestCase):
    def test_no_arbitrary_column_cap(self):
        cols = [f'c{i}' for i in range(120)]
        self.assertEqual(_validate(cols, None, None, 2, 5.0, 3), cols)

    def test_batch_size_is_not_source_size_limit(self):
        self.assertEqual(_validate(['x'], None, None, 1, 5.0, 3), ['x'])

    def test_bad_columns_rejected(self):
        with self.assertRaises(ValueError):
            _validate(['x'], None, ['y'], 1, 5.0, 3)

    def test_boundaries_across_chunks(self):
        def source():
            for d in ['2020-01-01 00:00:00', '2020-01-01 01:00:00',
                      '2020-01-01 01:00:00', '2020-01-01 07:00:00']:
                yield {'t': d, 'x': 5}
        boundaries = list(_boundaries(source(), time_column='t', columns=['x'],
                                     baseline=3600, gap_multiplier=5))
        self.assertEqual([(b['after_row'], b['reasons'][0]) for b in boundaries],
                         [(2, 'repeated_timestamp'), (3, 'large_observed_gap')])

    def test_spans_preserve_every_row_and_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'boundaries.jsonl'
            with path.open('w') as stream:
                for i in (3, 4, 12, 17):
                    stream.write(json.dumps({'after_row': i, 'reasons': ['test']}) + '\n')
            spans = list(_spans(path, 22, 2))
            self.assertEqual(spans[0][0], 0)
            self.assertEqual(spans[-1][1], 22)
            self.assertEqual(sum(b-a for a,b,_ in spans), 22)
            self.assertTrue(all(spans[i][1] == spans[i+1][0] for i in range(len(spans)-1)))
            self.assertTrue(any(role == 'transition_neighborhood' for _,_,role in spans))

    def test_more_than_100_regions_without_loss(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'boundaries.jsonl'
            with path.open('w') as stream:
                for p in range(5, 1500, 10):
                    stream.write(json.dumps({'after_row': p}) + '\n')
            spans = list(_spans(path, 1500, 2))
            self.assertGreater(len(spans), 100)
            self.assertEqual(sum(b-a for a,b,_ in spans), 1500)

    def test_positive_and_attention_within_same_region(self):
        rows = [{'t': '2020-01-01 00:00:00', 'x': 2, 'y': 5},
                {'t': '2020-01-01 00:00:00', 'x': 3, 'y': None}]
        findings = list(_region_findings(iter(rows), 0, 2,
                                         columns=['x', 'y'], time_column='t', region_id='r'))
        kinds = {(f['column'], f['polarity']) for f in findings}
        self.assertIn(('x', 'positive'), kinds)
        self.assertIn(('y', 'attention'), kinds)
        self.assertIn(('t', 'attention'), kinds)

    def test_no_calendar_or_time_column_required(self):
        rows = [{'x': 1}, {'x': None}, {'x': 2}]
        events = list(_boundaries(rows, time_column=None, columns=['x'], baseline=None, gap_multiplier=5))
        self.assertEqual([e['after_row'] for e in events], [1,2])


try:
    import duckdb
except ImportError:
    duckdb = None


@unittest.skipIf(duckdb is None, 'DuckDB required for source integration')
class DuckDBIntegrationTests(unittest.TestCase):
    def _file(self, folder, rows):
        p = Path(folder) / 'input.csv'
        p.write_text('t,x,y\n' + '\n'.join(rows) + '\n', encoding='utf-8')
        return p

    def test_exact_entire_source_and_manifest(self):
        from rawsight.quality_region_execution_v2 import execute_quality_regions_v2
        with tempfile.TemporaryDirectory() as folder:
            p = self._file(folder, [
                '2020-01-01 00:00:00,2,ok',
                '2020-01-01 01:00:00,3,ok',
                '2020-01-01 01:00:00,,ok',
                '2020-01-01 10:00:00,4,ok',
                '2020-01-01 11:00:00,5,ok',
            ])
            original = p.read_bytes()
            r = execute_quality_regions_v2(file_path=str(p), time_column='t',
                                            columns=['x', 'y'], batch_size=2,
                                            result_dir=str(Path(folder) / 'results'))
            self.assertEqual(r['status'], 'complete')
            self.assertEqual(r['region_coverage']['rows_evaluated'], 5)
            self.assertEqual(r['whole_source_quality']['temporal']['extra_rows_beyond_unique_timestamps'], 1)
            b = [json.loads(s) for s in Path(r['discovery']['boundaries_jsonl']).read_text().splitlines()]
            self.assertEqual([x['after_row'] for x in b], [2, 3])
            records = [json.loads(s) for s in Path(r['region_quality']['evidence_jsonl']).read_text().splitlines()]
            regions = [x for x in records if x['record_type'] == 'region']
            self.assertEqual(sum(x['stop']-x['start'] for x in regions), 5)
            self.assertEqual(p.read_bytes(), original)

    def test_large_region_count_does_not_trigger_limit(self):
        from rawsight.quality_region_execution_v2 import execute_quality_regions_v2
        with tempfile.TemporaryDirectory() as folder:
            start = datetime(2020, 1, 1)
            rows = [f'{start + timedelta(hours=i // 2):%Y-%m-%d %H:%M:%S},{i},yes'
                    for i in range(400)]
            p = self._file(folder, rows)
            r = execute_quality_regions_v2(file_path=str(p), time_column='t',
                                            columns=['x'], batch_size=7,
                                            result_dir=str(Path(folder) / 'results'))
            self.assertEqual(r['status'], 'complete')
            self.assertEqual(r['region_coverage']['rows_evaluated'], 400)
            self.assertEqual(r['discovery']['total_boundaries'], 200)
            self.assertGreater(r['discovery']['regions'], 0)


if __name__ == '__main__':
    unittest.main()
