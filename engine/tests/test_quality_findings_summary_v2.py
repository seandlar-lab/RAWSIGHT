import json
from pathlib import Path
import tempfile
import unittest

from rawsight.quality_findings_summary_v2 import summarize_quality_areas_v2


def fixtures(root: Path, transitions=2, n_stable=8):
    evid = root / 'evidence.jsonl'
    bound = root / 'boundaries.jsonl'
    areas = []
    boundaries = []
    cursor = 0
    for idx in range(transitions * 2 + 1):
        role = 'between_transitions' if idx % 2 == 0 else 'transition_neighborhood'
        rows = n_stable if role == 'between_transitions' else 2
        aid = f'region_{idx+1:09d}'
        areas.append({'record_type':'region','id':aid,'kind':'row_range','start':cursor,'stop':cursor+rows,'discovery_role':role})
        areas.append({'record_type':'finding','region_id':aid,'column':'x','kind':'complete_column','polarity':'positive','evidence':{'rows':rows,'missing':0},'interpretation_status':'observed'})
        areas.append({'record_type':'finding','region_id':aid,'column':'time','kind':'time_structure',
                      'polarity':'positive' if role=='between_transitions' else 'insufficient',
                      'evidence':{'valid_timestamps':rows,'invalid_timestamps':0,'adjacent_equal_timestamps':0,'adjacent_reversals':0,'positive_intervals':rows-1,'positive_intervals_all_equal':True if rows>=3 else None},'interpretation_status':'observed'})
        if role == 'transition_neighborhood':
            boundaries.append({'before_row':cursor-1,'after_row':cursor,'reasons':['large_observed_gap']})
        cursor += rows
    evid.write_text('\n'.join(json.dumps(x) for x in areas)+'\n',encoding='utf-8')
    bound.write_text('\n'.join(json.dumps(x) for x in boundaries)+'\n',encoding='utf-8')
    return evid,bound,cursor,transitions*2+1,(transitions*2+1)*2

class QualitySummaryV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.args = fixtures(self.root)
    def tearDown(self): self.tmp.cleanup()
    def call(self, **kwargs):
        e,b,n,areas,findings=self.args
        return summarize_quality_areas_v2(evidence_path=str(e),boundaries_path=str(b),source_rows=n,expected_areas=areas,expected_findings=findings,**kwargs)
    def test_complete_read_and_roles(self):
        r=self.call()
        self.assertEqual(r['coverage']['areas'],5)
        self.assertEqual(r['coverage']['findings'],10)
        self.assertEqual(r['area_roles']['transition_neighborhood']['rows'],4)
        self.assertEqual(r['method_effects']['transition_areas_with_insufficient_time_evidence'],2)
        self.assertEqual(r['boundary_reasons'], {'large_observed_gap':2})
    def test_method_is_not_called_bad_data(self):
        r=self.call()
        self.assertEqual(r['finding_counts']['insufficient'],2)
        self.assertIn('metodbegränsning',r['method_effects']['interpretation'])
        self.assertFalse(r['coverage']['source_order_certified'])
    def test_all_examples_are_traceable(self):
        r=self.call(examples_per_group=1)
        self.assertEqual(len(r['examples']['continuity_examples']),1)
        self.assertEqual(r['examples']['continuity_examples'][0]['rows'],8)
        self.assertEqual(r['examples']['continuity_examples'][0]['area_ref']['line'],1)
    def test_examples_zero_does_not_change_totals(self):
        r=self.call(examples_per_group=0)
        self.assertEqual(r['coverage']['findings'],10)
        self.assertTrue(all(not v for v in r['examples'].values()))
    def test_many_areas_no_input_cap(self):
        self.args=fixtures(self.root,transitions=150,n_stable=3)
        r=self.call(examples_per_group=2)
        self.assertEqual(r['coverage']['areas'],301)
        self.assertEqual(r['coverage']['boundary_events'],150)
        self.assertEqual(len(r['examples']['transition_examples']),2)
    def test_bad_partition_rejected(self):
        e,*_=self.args
        data=[json.loads(x) for x in e.read_text().splitlines()]
        data[3]['start']+=1
        e.write_text('\n'.join(map(json.dumps,data))+'\n')
        with self.assertRaisesRegex(ValueError,'Noncontiguous'):
            self.call()
    def test_missing_evidence_rejected(self):
        e,*_=self.args
        data=[json.loads(x) for x in e.read_text().splitlines()]
        data[1]['evidence']['rows']+=1
        e.write_text('\n'.join(map(json.dumps,data))+'\n')
        with self.assertRaisesRegex(ValueError,'mismatch'):
            self.call()
    def test_wrong_expected_count_rejected(self):
        with self.assertRaisesRegex(ValueError,'Area count'):
            summarize_quality_areas_v2(evidence_path=str(self.args[0]), boundaries_path=str(self.args[1]), source_rows=self.args[2], expected_areas=42)
    def test_negative_examples_rejected(self):
        with self.assertRaises(ValueError): self.call(examples_per_group=-1)
    def test_reversed_boundary_rejected(self):
        _,b,*_=self.args
        data=[json.loads(x) for x in b.read_text().splitlines()]
        data.reverse()
        b.write_text('\n'.join(map(json.dumps,data))+'\n')
        with self.assertRaisesRegex(ValueError,'Out-of-order'):
            self.call()

if __name__=='__main__': unittest.main()
