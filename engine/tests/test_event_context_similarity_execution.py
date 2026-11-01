"""Contract tests for bounded gap discovery and multiseries comparison adapter."""
import unittest
from unittest.mock import patch
from rawsight import event_context_similarity_execution as ex

AXIS = {'column':'timestamp', 'kind':'timestamp'}
GAPS = [
    {'id':'g1','anchor':{'kind':'temporal_gap','before_time':'2020-01-01T00:00:10','after_time':'2020-01-01T00:02:00'},'gap_seconds':110.0},
    {'id':'g2','anchor':{'kind':'temporal_gap','before_time':'2020-01-02T00:00:10','after_time':'2020-01-02T00:02:00'},'gap_seconds':110.0},
]

class FakeContext:
    is_open = True
    column_names = ['timestamp','A','B']
    column_types = ['TIMESTAMP','DOUBLE','DOUBLE']
    def assert_source(self, path):
        if path != 'source.csv': raise ValueError('source mismatch')


def source_rows(endpoint, side, n):
    # Different dates for the second event but matching patterns and cadence.
    base = endpoint[:10]
    if side == 'before':
        minutes = ['00:00:00', '00:00:05', '00:00:10']
        a = [1., 2., 3.]
    else:
        minutes = ['00:02:00', '00:02:05', '00:02:10']
        a = [3., 2., 1.]
    return [{'time': f'{base}T{t}', 'A':x, 'B':x*10} for t,x in zip(minutes,a)][:n]

class ExecutionTests(unittest.TestCase):
    def run_adapter(self, **kwargs):
        with patch.object(ex, '_find_gaps', return_value=[dict(x) for x in GAPS]), \
             patch.object(ex, '_side_rows', side_effect=lambda c,a,cols,endpoint,side,n: source_rows(endpoint,side,n)), \
             patch.object(ex, 'execute_event_context', side_effect=lambda **kw: {
                 'before':{'observation_count':3},'after':{'observation_count':3}}), \
             patch.object(ex, '_validate_temporal_axis', return_value=0), \
             patch.object(ex, '_is_numeric_type', side_effect=lambda t: t=='DOUBLE'):
            return ex.execute_event_context_similarity(file_path='source.csv',temporal_axis=AXIS,
                selected_columns=['A','B'],expected_interval_seconds=5,
                points_per_side=3, source_context=FakeContext(), **kwargs)

    def test_both_sides_multiseries(self):
        result=self.run_adapter()
        self.assertEqual(result['status'],'measured')
        self.assertEqual(len(result['events']),2)
        cand=result['comparison']['candidates'][0]
        self.assertEqual(cand['status'],'measured')
        self.assertAlmostEqual(cand['full_context_similarity'],1.0)
        self.assertEqual(result['events'][0]['context_observation_counts']['before'],3)
        self.assertIsNone(cand['temporal_comparability']['before']['warning'])

    def test_explicit_target(self):
        self.assertEqual(self.run_adapter(target_event_id='g2')['target_event_id'],'g2')

    def test_missing_target_rejected(self):
        with self.assertRaisesRegex(ValueError,'not found'):
            self.run_adapter(target_event_id='other')

    def test_invalid_signal_selection(self):
        with self.assertRaises(ValueError):
            ex.execute_event_context_similarity(file_path='x',temporal_axis=AXIS,
                selected_columns=[],expected_interval_seconds=5)

    def test_reject_duplicate_signals(self):
        with self.assertRaises(ValueError):
            ex.execute_event_context_similarity(file_path='x',temporal_axis=AXIS,
                selected_columns=['A','A'],expected_interval_seconds=5)

    def test_reject_invalid_cap(self):
        with self.assertRaises(ValueError):
            ex.execute_event_context_similarity(file_path='x',temporal_axis=AXIS,
                selected_columns=['A'],expected_interval_seconds=5,max_events=1)

    def test_reject_invalid_interval(self):
        with self.assertRaises(ValueError):
            ex.execute_event_context_similarity(file_path='x',temporal_axis=AXIS,
                selected_columns=['A'],expected_interval_seconds=0)

    def test_reject_unknown_numeric_column(self):
        with patch.object(ex, '_validate_temporal_axis', return_value=0), \
             patch.object(ex, '_is_numeric_type', side_effect=lambda t: t=='DOUBLE'):
            with self.assertRaisesRegex(ValueError,'numeric'):
                ex.execute_event_context_similarity(file_path='source.csv',temporal_axis=AXIS,
                    selected_columns=['NOPE'],expected_interval_seconds=5,source_context=FakeContext())

    def test_reject_reversed_scan_window(self):
        with self.assertRaisesRegex(ValueError, 'earlier'):
            ex.execute_event_context_similarity(file_path='x', temporal_axis=AXIS,
                selected_columns=['A'], expected_interval_seconds=5,
                gap_scan_start='2020-04-03T00:00:00', gap_scan_end='2020-04-01T00:00:00')

    def test_reject_timezone_aware_scan_window(self):
        with self.assertRaisesRegex(ValueError, 'timezone-naive'):
            ex.execute_event_context_similarity(file_path='x', temporal_axis=AXIS,
                selected_columns=['A'], expected_interval_seconds=5,
                gap_scan_start='2020-04-01T00:00:00+02:00')

    def test_scan_bounds_passed_to_discovery(self):
        with patch.object(ex, '_find_gaps', return_value=[dict(GAPS[0])]) as mock_scan, \
             patch.object(ex, '_validate_temporal_axis', return_value=0), \
             patch.object(ex, '_is_numeric_type', side_effect=lambda t: t=='DOUBLE'):
            result=ex.execute_event_context_similarity(file_path='source.csv',temporal_axis=AXIS,
                selected_columns=['A'],expected_interval_seconds=5,source_context=FakeContext(),
                gap_scan_start='2020-04-01T00:00:00',gap_scan_end='2020-04-05T00:00:00')
        self.assertEqual(result['status'], 'insufficient_events')
        self.assertEqual(mock_scan.call_args.args[-2].isoformat(), '2020-04-01T00:00:00')
        self.assertEqual(mock_scan.call_args.args[-1].isoformat(), '2020-04-05T00:00:00')

    def test_only_one_event(self):
        with patch.object(ex, '_find_gaps', return_value=[dict(GAPS[0])]), \
             patch.object(ex, '_validate_temporal_axis', return_value=0), \
             patch.object(ex, '_is_numeric_type', side_effect=lambda t: t=='DOUBLE'):
            result=ex.execute_event_context_similarity(file_path='source.csv',temporal_axis=AXIS,
                selected_columns=['A'],expected_interval_seconds=5,source_context=FakeContext())
        self.assertEqual(result['status'],'insufficient_events')

    def test_contiguous_tail_disallows_crossing_gaps(self):
        rows=[{'time':f'2020-01-01T00:00:{n:02d}','A':float(n)} for n in (0,10,20,50)]
        self.assertEqual(len(ex._contiguous_tail(rows,'before',15)),1)
        self.assertEqual(len(ex._contiguous_tail(rows,'after',15)),3)

    def test_alignment_insufficient_if_short(self):
        payload=ex._aligned_side([{'A':1.0}],['A'],3)
        self.assertEqual(payload['series']['A'],[None,None,None])

if __name__=='__main__': unittest.main()
