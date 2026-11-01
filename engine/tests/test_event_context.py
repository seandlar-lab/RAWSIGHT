import unittest
from rawsight.event_context import analyze_event_context


def sample():
    return [
      {'time':'2020-01-01T00:00:00','A':1,'B':10},
      {'time':'2020-01-01T00:00:10','A':2,'B':None},
      {'time':'2020-01-01T00:00:20','A':3,'B':12},
      {'time':'2020-01-01T01:00:00','A':4,'B':20},
      {'time':'2020-01-01T01:00:10','A':5,'B':21},
      {'time':'2020-01-01T01:00:20','A':6,'B':22},
    ]


def run(anchor, rows=None, **kw):
    return analyze_event_context(rows if rows is not None else sample(),anchor=anchor,selected_columns=['A','B'],expected_interval_seconds=10,**kw)


GAP={'kind':'temporal_gap','before_time':'2020-01-01T00:00:20','after_time':'2020-01-01T01:00:00'}
class EventContextTests(unittest.TestCase):
    def test_gap_context_and_deltas(self):
        r=run(GAP)
        self.assertEqual(r['status'],'measured')
        self.assertEqual(r['before']['observation_count'],3)
        self.assertEqual(r['after']['observation_count'],3)
        self.assertEqual(r['before']['columns']['A']['delta'],2)
        self.assertEqual(r['after']['columns']['A']['delta'],2)
        self.assertEqual(r['anchor']['gap_seconds'],3580)
    def test_missingness_exposed(self):
        r=run(GAP)
        self.assertEqual(r['before']['columns']['B']['coverage'],2/3)
        self.assertEqual(r['before']['columns']['B']['delta'],2)
    def test_point_event_excludes_anchor(self):
        r=run({'kind':'point_event','time':'2020-01-01T00:00:10','label':'extreme_value'})
        self.assertEqual(r['anchor_values']['A'],2)
        self.assertEqual(r['before']['observation_count'],1)
        self.assertEqual(r['after']['observation_count'],1)
    def test_point_context_does_not_cross_gap(self):
        r=run({'kind':'point_event','time':'2020-01-01T01:00:00'})
        self.assertEqual(r['before']['observation_count'],0)
        self.assertEqual(r['after']['observation_count'],2)
        self.assertEqual(r['status'],'insufficient_context')
    def test_wrong_gap_rejected(self):
        with self.assertRaises(ValueError):
            run({'kind':'temporal_gap','before_time':'2020-01-01T00:00:00','after_time':'2020-01-01T01:00:00'})
    def test_not_a_gap_rejected(self):
        with self.assertRaises(ValueError):
            run({'kind':'temporal_gap','before_time':'2020-01-01T00:00:00','after_time':'2020-01-01T00:00:10'})
    def test_duplicates_rejected(self):
        rows=sample();rows.insert(1,dict(rows[0]))
        with self.assertRaises(ValueError):
            run(GAP,rows)
    def test_window_limit(self):
        r=run(GAP,before_points=2,after_points=1)
        self.assertEqual(r['before']['observation_count'],2)
        self.assertEqual(r['after']['observation_count'],1)
    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            run(GAP,before_points=0)
        with self.assertRaises(ValueError):
            run(GAP,gap_multiple=1)
    def test_no_source_mutation(self):
        rows=sample();original=[dict(v) for v in rows]
        run(GAP,rows)
        self.assertEqual(rows,original)

if __name__=='__main__': unittest.main()
