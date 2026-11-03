"""Tests for the v0.1 streaming evidence summary."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from rawsight.quality_findings_summary import summarize_quality_findings, summarize_quality_run


def write_lines(path, records):
    with path.open('w', encoding='utf-8') as handle:
        for rec in records:
            handle.write(json.dumps(rec) + '\n')


def region(i, a, b):
    return {'record_type': 'region', 'id': f'region_{i:09d}', 'kind': 'row_range',
            'start': a, 'stop': b, 'discovery_role': 'between_transitions'}


def finding(i, polarity='positive', kind='complete_column', col='x', **evidence):
    return {'record_type': 'finding', 'region_id': f'region_{i:09d}', 'column': col,
            'kind': kind, 'polarity': polarity, 'evidence': evidence,
            'interpretation_status': 'observed'}


class SummaryTests(unittest.TestCase):
    def run_case(self, records, *, n=None, regions=None, findings=None, boundary_records=None, limit=3):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'evidence.jsonl'
            write_lines(path, records)
            bp = None
            if boundary_records is not None:
                bp = Path(folder) / 'boundaries.jsonl'
                write_lines(bp, boundary_records)
            return summarize_quality_findings(evidence_path=str(path),
                                              boundaries_path=str(bp) if bp else None,
                                              source_rows=n, expected_regions=regions,
                                              expected_findings=findings,
                                              examples_per_polarity=limit)

    def test_counts_categories_and_exact_coverage(self):
        r = self.run_case([region(1, 0, 3), finding(1, 'positive'),
                           finding(1, 'attention', 'missing_values', 'x', rows=3, missing=1),
                           region(2, 3, 5), finding(2, 'insufficient', 'time_structure', 't',
                                                  valid_timestamps=2, positive_intervals=0)],
                          n=5, regions=2, findings=3, boundary_records=[{'after_row': 3}])
        self.assertEqual(r['finding_counts'], {'positive': 1, 'attention': 1, 'insufficient': 1})
        self.assertEqual(r['coverage']['boundary_event_count'], 1)
        self.assertEqual(r['coverage']['rows_in_regions'], 5)
        self.assertTrue(r['coverage']['exhaustive_evidence_read'])
        self.assertEqual(r['examples']['attention'][0]['evidence_ref']['line'], 3)

    def test_all_findings_counted_but_examples_bounded(self):
        records = []
        for i in range(1, 1001):
            records += [region(i, i-1, i), finding(i)]
        r = self.run_case(records, n=1000, regions=1000, findings=1000, limit=2)
        self.assertEqual(r['finding_counts']['positive'], 1000)
        self.assertEqual(len(r['examples']['positive']), 2)
        self.assertEqual(r['coverage']['region_count'], 1000)

    def test_attention_and_positive_same_region(self):
        r = self.run_case([region(1, 0, 4), finding(1),
                           finding(1, 'attention', 'time_structure', 't', adjacent_equal_timestamps=2)], n=4)
        self.assertEqual(len(r['examples']['positive']), 1)
        self.assertEqual(len(r['examples']['attention']), 1)
        self.assertIn('upprepade', r['examples']['attention'][0]['explanation'])

    def test_reject_missing_rows_or_noncontiguous_regions(self):
        with self.assertRaisesRegex(ValueError, 'Noncontiguous'):
            self.run_case([region(1, 0, 2), finding(1), region(2, 3, 4), finding(2)])
        with self.assertRaisesRegex(ValueError, 'Coverage mismatch'):
            self.run_case([region(1, 0, 2), finding(1)], n=3)

    def test_reject_mismatched_counts(self):
        with self.assertRaisesRegex(ValueError, 'Finding count mismatch'):
            self.run_case([region(1, 0, 1), finding(1)], findings=2)
        with self.assertRaisesRegex(ValueError, 'Region count mismatch'):
            self.run_case([region(1, 0, 1), finding(1)], regions=2)

    def test_reject_orphan_finding_and_unknown_polarity(self):
        with self.assertRaisesRegex(ValueError, 'matching preceding region'):
            self.run_case([finding(1)])
        with self.assertRaisesRegex(ValueError, 'Unknown finding polarity'):
            self.run_case([region(1, 0, 1), finding(1, 'unverified')])

    def test_reject_bad_json_and_boundary(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'a.jsonl'
            path.write_text('bad json\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Invalid JSONL'):
                summarize_quality_findings(evidence_path=str(path))
        with self.assertRaisesRegex(ValueError, 'Invalid boundary'):
            self.run_case([region(1, 0, 2), finding(1)], n=2,
                          boundary_records=[{'after_row': 3}])

    def test_no_unsupported_significance_claim(self):
        r = self.run_case([region(1, 0, 1), finding(1)], n=1)
        self.assertIn('not statistical significance', r['interpretation']['priority_meaning'])
        self.assertIn('not certified truth', r['interpretation']['positive_meaning'])

    def test_wrapper_requires_completed_exhaustive_run(self):
        with self.assertRaises(ValueError):
            summarize_quality_run({'analysis_kind': 'quality_region_execution', 'status': 'failed'})
        with self.assertRaises(ValueError):
            summarize_quality_run({'analysis_kind': 'quality_region_execution', 'status': 'complete',
                                   'region_coverage': {'exhaustive': False, 'rows_evaluated': 1,
                                                       'source_rows': 2}})

    def test_no_time_dimension(self):
        r = self.run_case([region(1, 0, 2), finding(1, 'positive', 'complete_column', 'category', rows=2, missing=0)], n=2)
        self.assertEqual(r['coverage']['rows_in_regions'], 2)
        self.assertEqual(r['examples']['positive'][0]['column'], 'category')


if __name__ == '__main__':
    unittest.main()
