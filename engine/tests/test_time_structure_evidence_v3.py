"""Unit contract for descriptive, non-alarmist time interval evidence."""
import json
from pathlib import Path
import tempfile
import unittest

from rawsight.quality_region_execution_v3 import _region_findings_v3
from rawsight.quality_findings_summary_v3 import summarize_quality_areas_v3


def findings(seconds, *, baseline=10.0):
    from datetime import datetime, timedelta
    base = datetime(2020, 1, 1)
    rows = [{'t': base + timedelta(seconds=s), 'x': s} for s in seconds]
    return list(_region_findings_v3(iter(rows), 0, len(rows), columns=['x'],
                                    time_column='t', region_id='region_000000001',
                                    baseline_seconds=baseline))[-1]


class TimeIntervalTests(unittest.TestCase):
    def test_variable_positive_intervals_are_informational(self):
        f = findings([0, 10, 20, 31, 41])
        self.assertEqual(f['polarity'], 'informational')
        d = f['evidence']['positive_interval_distribution']
        self.assertEqual(d['count'], 4)
        self.assertEqual(d['min_seconds'], 10)
        self.assertEqual(d['max_seconds'], 11)
        self.assertEqual(d['exact_baseline_matches'], 3)
        self.assertAlmostEqual(d['mean_seconds'], 10.25)
        self.assertAlmostEqual(d['population_stddev_seconds'], 0.4330127019)

    def test_equal_intervals_are_positive(self):
        f = findings([0, 10, 20, 30])
        self.assertEqual(f['polarity'], 'positive')
        self.assertTrue(f['evidence']['positive_intervals_all_equal'])

    def test_two_rows_are_insufficient(self):
        f = findings([0, 10])
        self.assertEqual(f['polarity'], 'insufficient')
        self.assertEqual(f['evidence']['positive_interval_distribution']['count'], 1)

    def test_repeated_time_is_still_attention(self):
        f = findings([0, 10, 10, 20])
        self.assertEqual(f['polarity'], 'attention')
        self.assertEqual(f['evidence']['adjacent_equal_timestamps'], 1)

    def test_reverse_time_is_still_attention(self):
        f = findings([0, 10, 5, 20])
        self.assertEqual(f['polarity'], 'attention')
        self.assertEqual(f['evidence']['adjacent_reversals'], 1)

    def test_missing_timestamp_is_attention(self):
        from datetime import datetime
        rows = [{'t': datetime(2020, 1, 1), 'x': 1},
                {'t': None, 'x': 2},
                {'t': datetime(2020, 1, 1, 0, 0, 10), 'x': 3}]
        f = list(_region_findings_v3(rows, 0, 3, columns=['x'], time_column='t',
                                     region_id='region_000000001'))[-1]
        self.assertEqual(f['polarity'], 'attention')
        self.assertEqual(f['evidence']['invalid_timestamps'], 1)

    def test_streaming_iterable_consumed_once(self):
        f = findings([i * 10 + (i % 7) for i in range(10000)])
        self.assertEqual(f['evidence']['positive_intervals'], 9999)
        self.assertEqual(f['polarity'], 'informational')

    def test_summary_understands_informational(self):
        time_finding = findings([0, 10, 21, 31])
        with tempfile.TemporaryDirectory() as temp:
            evid = Path(temp) / 'evid.jsonl'
            bound = Path(temp) / 'bound.jsonl'
            records = [dict(record_type='region', id='region_000000001', kind='row_range',
                            start=0, stop=4, discovery_role='between_transitions'),
                       dict(record_type='finding', region_id='region_000000001', column='x',
                            kind='complete_column', polarity='positive',
                            evidence={'rows':4,'missing':0}, interpretation_status='observed'),
                       time_finding]
            evid.write_text(''.join(json.dumps(x) + '\n' for x in records), encoding='utf-8')
            bound.write_text('', encoding='utf-8')
            r = summarize_quality_areas_v3(evidence_path=str(evid), boundaries_path=str(bound),
                                           source_rows=4, expected_areas=1, expected_findings=2)
            self.assertEqual(r['finding_counts']['informational'], 1)
            self.assertEqual(r['time_evidence']['variable_time_areas'], 1)
            self.assertEqual(r['time_interval_distribution_coverage']['positive_intervals_described'], 3)
            self.assertEqual(len(r['examples']['variability_examples']), 1)

    def test_summary_legacy_evidence_still_parses(self):
        with tempfile.TemporaryDirectory() as temp:
            evid = Path(temp) / 'evid.jsonl'
            bound = Path(temp) / 'bound.jsonl'
            records = [dict(record_type='region', id='region_000000001', kind='row_range',
                            start=0, stop=3, discovery_role='between_transitions'),
                       dict(record_type='finding', region_id='region_000000001', column='t',
                            kind='time_structure', polarity='attention',
                            evidence={'valid_timestamps':3,'invalid_timestamps':0,
                                      'adjacent_equal_timestamps':0,'adjacent_reversals':0,
                                      'positive_intervals':2,'positive_intervals_all_equal':False},
                            interpretation_status='observed')]
            evid.write_text(''.join(json.dumps(x) + '\n' for x in records), encoding='utf-8')
            bound.write_text('', encoding='utf-8')
            r = summarize_quality_areas_v3(evidence_path=str(evid), boundaries_path=str(bound),
                                           source_rows=3)
            self.assertEqual(r['finding_counts']['attention'], 1)
            self.assertEqual(r['time_interval_distribution_coverage']['areas_with_distribution'], 0)


if __name__ == '__main__':
    unittest.main()
