"""Deterministic source-context tests, no dataset-specific column names."""
import unittest
from datetime import datetime, timedelta

from rawsight.event_context_execution import execute_event_context

START = datetime(2020,1,1)
AXIS = {'orientation':'vertical','sequence_index':0}
GAP = {'kind':'temporal_gap','before_time':(START+timedelta(seconds=20)).isoformat(),
       'after_time':(START+timedelta(seconds=100)).isoformat()}
BASE = dict(file_path='synthetic.csv', temporal_axis=AXIS,
            selected_columns=['a','b'],expected_interval_seconds=10)


def rows(*seconds):
    return [(START+timedelta(seconds=s),float(s),float(s*2)) for s in seconds]

class FakeCursor:
    def __init__(self, rows): self.rows=rows
    def fetchall(self): return self.rows

class FakeConnection:
    def __init__(self, records):
        self.records=records
        self.sqls=[]
    def execute(self,sql,args):
        self.sqls.append((sql,args))
        if 'SELECT 1 FROM normalized' in sql:
            a,b=(datetime.fromisoformat(x) for x in args)
            return FakeCursor([(1,)] if any(a<row[0]<b for row in self.records) else [])
        p=datetime.fromisoformat(args[0]); lim=args[-1]
        if 'observation_time < CAST' in sql and 'observation_time <=' not in sql:
            selected=[r for r in self.records if r[0]<p]
        elif 'observation_time <= CAST' in sql:
            selected=[r for r in self.records if r[0]<=p]
        elif 'observation_time >= CAST' in sql:
            selected=[r for r in self.records if r[0]>=p]
        elif 'observation_time > CAST' in sql:
            selected=[r for r in self.records if r[0]>p]
        else:
            selected=[r for r in self.records if r[0]==p]
        return FakeCursor(sorted(selected,key=lambda r:r[0],reverse='DESC' in sql)[:lim])

class FakeContext:
    is_open=True
    view_name='rawsight_source'
    column_names=['t','a','b','tag']
    column_types=['TIMESTAMP','DOUBLE','INTEGER','VARCHAR']
    def __init__(self,records):self.conn=FakeConnection(records)
    def assert_source(self,file_path):
        if file_path!='synthetic.csv': raise ValueError('wrong source')
    def require_connection(self):return self.conn

class EventContextExecutionTests(unittest.TestCase):
    def run_gap(self,records,**opts):
        context=FakeContext(records)
        return execute_event_context(**{**BASE, **opts},anchor=GAP,source_context=context)

    def test_gap_windows_from_source(self):
        r=self.run_gap(rows(0,10,20,100,110,120),before_points=2,after_points=2)
        self.assertEqual(r['status'],'measured')
        self.assertEqual(r['before']['observation_count'],2)
        self.assertEqual(r['after']['observation_count'],2)
        self.assertEqual(r['anchor']['gap_seconds'],80)
        self.assertTrue(r['execution']['anchor_verified_against_source'])

    def test_nonconsecutive_anchor_rejected(self):
        with self.assertRaisesRegex(ValueError,'not consecutive'):
            self.run_gap(rows(0,10,20,50,100,110))

    def test_missing_endpoint_rejected(self):
        with self.assertRaisesRegex(ValueError,'endpoints'):
            self.run_gap(rows(0,10,100,110))

    def test_duplicate_endpoint_rejected(self):
        with self.assertRaisesRegex(ValueError,'unique'):
            self.run_gap(rows(10,20,20,100,110))

    def test_point_excludes_anchor(self):
        anchor={'kind':'point_event','time':(START+timedelta(seconds=20)).isoformat(),'label':'candidate_extreme'}
        r=execute_event_context(**BASE,anchor=anchor,source_context=FakeContext(rows(0,10,20,30,40)))
        self.assertEqual(r['before']['observation_count'],2)
        self.assertEqual(r['after']['observation_count'],2)
        self.assertEqual(r['anchor_values']['a'],20.0)

    def test_point_window_stops_at_another_gap(self):
        anchor={'kind':'point_event','time':(START+timedelta(seconds=100)).isoformat()}
        r=execute_event_context(**BASE,anchor=anchor,source_context=FakeContext(rows(0,10,20,100,110)))
        self.assertEqual(r['before']['observation_count'],0)
        self.assertEqual(r['after']['observation_count'],1)
        self.assertEqual(r['status'],'insufficient_context')

    def test_duplicate_point_rejected(self):
        anchor={'kind':'point_event','time':(START+timedelta(seconds=20)).isoformat()}
        with self.assertRaisesRegex(ValueError,'exactly one'):
            execute_event_context(**BASE,anchor=anchor,source_context=FakeContext(rows(10,20,20,30)))

    def test_non_numeric_column_rejected(self):
        with self.assertRaisesRegex(ValueError,'numeric'):
            self.run_gap(rows(10,20,100,110),selected_columns=['tag'])

    def test_resource_limit_rejects_not_truncates(self):
        with self.assertRaisesRegex(ValueError,'exceeds'):
            self.run_gap(rows(10,20,100,110),before_points=1001)

    def test_timezone_aware_anchor_rejected(self):
        anchor={**GAP,'before_time':'2020-01-01T00:00:20+01:00'}
        with self.assertRaisesRegex(ValueError,'timezone-naive'):
            execute_event_context(**BASE,anchor=anchor,source_context=FakeContext(rows(10,20,100,110)))

if __name__=='__main__':unittest.main()
