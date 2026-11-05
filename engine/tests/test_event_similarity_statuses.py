"""Regression tests for conservative, unscored Event Similarity failures."""
import unittest
from datetime import datetime
from unittest.mock import patch

from rawsight import event_context_similarity_execution as ex

AXIS = {'orientation': 'vertical', 'sequence_index': 0}
GAPS = [
    {'id': 'g1', 'anchor': {'kind': 'temporal_gap', 'before_time': '2020-01-01T00:00:10', 'after_time': '2020-01-01T00:02:00'}, 'gap_seconds': 110.0},
    {'id': 'g2', 'anchor': {'kind': 'temporal_gap', 'before_time': '2020-01-02T00:00:10', 'after_time': '2020-01-02T00:02:00'}, 'gap_seconds': 110.0},
]


class FakeCursor:
    def __init__(self, records):
        self.records = records
    def fetchall(self):
        return self.records


class FakeContext:
    is_open = True
    column_names = ['timestamp', 'A']
    column_types = ['TIMESTAMP', 'DOUBLE']
    view_name = 'rawsight_source'
    def __init__(self, records=()):
        self.records = records
    def assert_source(self, path):
        assert path == 'test.csv'
    def require_connection(self):
        return self
    def execute(self, sql, params):
        return FakeCursor(self.records)


class EventSimilarityStatusTests(unittest.TestCase):
    def run_adapter(self, gap_result, **patches):
        ctx = FakeContext()
        with patch.object(ex, '_find_gaps', side_effect=gap_result if isinstance(gap_result, BaseException) else None,
                          return_value=None if isinstance(gap_result, BaseException) else [dict(x) for x in gap_result]), \
             patch.object(ex, '_validate_temporal_axis', return_value=0), \
             patch.object(ex, '_is_numeric_type', return_value=True):
            return ex.execute_event_context_similarity(
                file_path='test.csv', temporal_axis=AXIS,
                selected_columns=['A'], expected_interval_seconds=5,
                source_context=ctx, points_per_side=3)

    def assert_unscored(self, result, status, code):
        self.assertEqual(result['status'], status)
        self.assertEqual(result['reason_code'], code)
        self.assertIsNone(result['comparison'])
        self.assertEqual(result['events'], [])
        self.assertTrue(result['limitations'])

    def test_duplicate_endpoint_from_scan_is_unscored(self):
        result = self.run_adapter(ex.InsufficientOrderingError('duplicate endpoint'))
        self.assert_unscored(result, 'insufficient_ordering', 'non_unique_gap_endpoint')

    def test_gap_cap_is_separate_resource_limit(self):
        result = self.run_adapter(ex.EventResourceLimitError('more than cap'))
        self.assert_unscored(result, 'resource_limit', 'gap_event_cap_exceeded')

    def test_duplicate_endpoint_from_trusted_anchor_is_unscored(self):
        with patch.object(ex, '_find_gaps', return_value=[dict(x) for x in GAPS]), \
             patch.object(ex, 'execute_event_context', side_effect=ValueError('Gap endpoints must have unique timestamps')), \
             patch.object(ex, '_validate_temporal_axis', return_value=0), \
             patch.object(ex, '_is_numeric_type', return_value=True):
            result = ex.execute_event_context_similarity(
                file_path='test.csv', temporal_axis=AXIS,
                selected_columns=['A'], expected_interval_seconds=5,
                source_context=FakeContext(), points_per_side=3)
        self.assert_unscored(result, 'insufficient_ordering', 'non_unique_gap_endpoint')

    def test_unrelated_anchor_validation_is_not_hidden(self):
        with patch.object(ex, '_find_gaps', return_value=[dict(x) for x in GAPS]), \
             patch.object(ex, 'execute_event_context', side_effect=ValueError('Source mismatch')), \
             patch.object(ex, '_validate_temporal_axis', return_value=0), \
             patch.object(ex, '_is_numeric_type', return_value=True):
            with self.assertRaisesRegex(ValueError, 'Source mismatch'):
                ex.execute_event_context_similarity(
                    file_path='test.csv', temporal_axis=AXIS,
                    selected_columns=['A'], expected_interval_seconds=5,
                    source_context=FakeContext(), points_per_side=3)

    def test_duplicate_in_window_is_unscored(self):
        with patch.object(ex, '_find_gaps', return_value=[dict(x) for x in GAPS]), \
             patch.object(ex, 'execute_event_context', return_value={'before': {'observation_count': 3}, 'after': {'observation_count': 3}}), \
             patch.object(ex, '_side_rows', return_value=[{'time':'2020-01-01T00:00:10', 'A':1.0}, {'time':'2020-01-01T00:00:10', 'A':2.0}]), \
             patch.object(ex, '_validate_temporal_axis', return_value=0), \
             patch.object(ex, '_is_numeric_type', return_value=True):
            result = ex.execute_event_context_similarity(
                file_path='test.csv', temporal_axis=AXIS,
                selected_columns=['A'], expected_interval_seconds=5,
                source_context=FakeContext(), points_per_side=3)
        self.assert_unscored(result, 'insufficient_ordering', 'non_unique_observation_window')

    def test_find_gaps_still_rejects_nonunique_endpoint(self):
        records = [(datetime(2020, 1, 1), datetime(2020, 1, 2), 86400, 2)]
        with patch.object(ex, '_validate_temporal_axis', return_value=0), \
             patch.object(ex, '_build_temporal_expression', return_value='"timestamp"'):
            with self.assertRaises(ex.InsufficientOrderingError):
                ex._find_gaps(FakeContext(records), AXIS, 5, 3, 20)

    def test_find_gaps_still_rejects_partial_event_scan(self):
        records = [(datetime(2020, 1, 1), datetime(2020, 1, 2), 86400, 1)] * 3
        with patch.object(ex, '_validate_temporal_axis', return_value=0), \
             patch.object(ex, '_build_temporal_expression', return_value='"timestamp"'):
            with self.assertRaises(ex.EventResourceLimitError):
                ex._find_gaps(FakeContext(records), AXIS, 5, 3, 2)


if __name__ == '__main__':
    unittest.main()
