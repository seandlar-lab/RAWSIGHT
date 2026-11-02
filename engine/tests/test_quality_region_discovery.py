import unittest
from copy import deepcopy
from rawsight.quality_region_discovery import discover_quality_regions

class AutomaticRegionDiscoveryTests(unittest.TestCase):
    def test_no_calendar_and_no_time(self):
        v = discover_quality_regions([{'x':1},{'x':2}])
        self.assertEqual(v['status'], 'whole_only')
        self.assertEqual(v['regions'], [{'id':'dataset','kind':'whole'}])
    def test_gap_keeps_both_sides(self):
        rows = [{'t': f'2020-01-01T0{i}:00:00', 'v':i} for i in range(4)]
        rows += [{'t': f'2020-01-10T0{i}:00:00', 'v':i} for i in range(4)]
        v = discover_quality_regions(rows, time_column='t')
        self.assertEqual(v['status'], 'partitioned')
        self.assertIn('large_observed_gap', v['boundaries'][0]['reasons'])
        self.assertEqual(v['boundaries'][0]['after_row'],4)
        parts = v['regions'][1:]
        self.assertEqual(sum(r['stop']-r['start'] for r in parts),len(rows))
        self.assertEqual(parts[0]['start'],0)
        self.assertEqual(parts[-1]['stop'],len(rows))
        try:
            from rawsight.quality_evidence import assess_quality
        except ModuleNotFoundError:
            self.skipTest("Existing RAWSIGHT quality_evidence module not mounted in isolated test container")
        assessed = assess_quality(rows,regions=[{'id':r['id'],'kind':'row_range','start':r['start'],'stop':r['stop']} for r in parts],time_column='t')
        self.assertEqual(len(assessed['regions']),len(parts))
    def test_repeated_timestamp_is_evidence_not_discarded(self):
        rows=[{'t':'2020-01-01T00:00:00'}, {'t':'2020-01-01T00:00:00'}, {'t':'2020-01-01T01:00:00'}]
        v=discover_quality_regions(rows,time_column='t')
        self.assertIn('repeated_timestamp',v['boundaries'][0]['reasons'])
        self.assertEqual(sum(r['stop']-r['start'] for r in v['regions'][1:]),3)
    def test_out_of_order(self):
        rows=[{'t':'2020-01-02'},{'t':'2020-01-01'},{'t':'2020-01-03'}]
        v=discover_quality_regions(rows,time_column='t')
        self.assertTrue(any('reversed_time' in b['reasons'] for b in v['boundaries']))
    def test_non_temporal_missingness(self):
        rows=[{'x':1}]*4+[{'x':None}]*4+[{'x':2}]*4
        v=discover_quality_regions(rows,value_columns=['x'])
        self.assertEqual(v['status'],'partitioned')
        self.assertEqual(len(v['boundaries']),2)
    def test_zero_rows(self):
        self.assertEqual(discover_quality_regions([])['status'],'insufficient_data')
    def test_source_immutable(self):
        rows=[{'t':'2020-01-01'},{'t':'2020-01-01'}]
        copied=deepcopy(rows)
        discover_quality_regions(rows,time_column='t')
        self.assertEqual(rows,copied)
    def test_budget_explicit_no_silent_partial_partition(self):
        rows=[{'x':None if (i//5)%2 else i} for i in range(100)]
        v=discover_quality_regions(rows,value_columns=['x'],max_regions=2)
        self.assertEqual(v['status'],'region_limit_exceeded')
        self.assertEqual(v['regions'],[{'id':'dataset','kind':'whole'}])
        self.assertGreater(v['total_boundaries'],2)
    def test_invalid_inputs(self):
        for opts in ({'max_regions':0},{'gap_multiplier':1},{'min_region_rows':0},{'value_columns':['x','x']}):
            with self.assertRaises(ValueError): discover_quality_regions([{'x':1}],**opts)
    def test_invalid_time_nonfatal(self):
        v=discover_quality_regions([{'t':'broken'}, {'t':'2020-01-01'}],time_column='t')
        self.assertEqual(v['status'],'partitioned')
        self.assertIn('invalid_timestamp_transition',v['boundaries'][0]['reasons'])
    def test_unaffected_uniform_series(self):
        rows=[{'t':f'2020-01-01T0{i}:00:00'} for i in range(5)]
        self.assertEqual(discover_quality_regions(rows,time_column='t')['status'],'whole_only')

if __name__=='__main__': unittest.main()
