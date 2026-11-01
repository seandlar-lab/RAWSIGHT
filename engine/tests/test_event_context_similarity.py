import unittest
from rawsight.event_context_similarity import compare_event_contexts

def event(id, before, after, method='observation_index'):
    return {'id':id, 'before':{'series':before,'alignment':{'method':method,'bin_count':5}},
            'after':{'series':after,'alignment':{'method':method,'bin_count':5}}}

class EventContextSimilarityTests(unittest.TestCase):
    def setUp(self):
        self.target=event('target',{'a':[1,2,3,4,5],'b':[5,4,3,2,1]},
                          {'a':[2,3,4,5,6],'b':[1,2,3,4,5]})
    def compare(self,candidates,**kwargs):
        return compare_event_contexts(self.target,candidates,selected_columns=['a','b'],**kwargs)
    def test_matching_both_sides(self):
        r=self.compare([event('match',{'a':[2,4,6,8,10],'b':[10,8,6,4,2]},
                              {'a':[1,2,3,4,5],'b':[6,7,8,9,10]})])
        self.assertEqual(r['status'],'measured')
        self.assertAlmostEqual(r['candidates'][0]['full_context_similarity'],1.0)
        self.assertEqual(r['candidates'][0]['sides']['before']['measured_signal_count'],2)
    def test_opposite_after_remains_explicit(self):
        r=self.compare([event('reverse',{'a':[1,2,3,4,5],'b':[5,4,3,2,1]},
                              {'a':[6,5,4,3,2],'b':[5,4,3,2,1]})])
        c=r['candidates'][0]
        self.assertAlmostEqual(c['sides']['before']['shape_similarity'],1)
        self.assertAlmostEqual(c['sides']['after']['shape_similarity'],0)
        self.assertAlmostEqual(c['full_context_similarity'],.5)
    def test_missing_after_no_full_score(self):
        r=self.compare([event('missing',{'a':[1,2,3,4,5],'b':[5,4,3,2,1]},
                              {'a':[None]*5,'b':[None]*5})])
        self.assertEqual(r['candidates'][0]['status'],'partial_evidence')
        self.assertIsNone(r['candidates'][0]['full_context_similarity'])
        self.assertEqual(r['candidates'][0]['sides']['before']['status'],'measured')
    def test_minimum_measured_signals(self):
        r=self.compare([event('one',{'a':[1,2,3,4,5]}, {'a':[2,3,4,5,6]})],minimum_measured_signals=2)
        self.assertEqual(r['status'],'insufficient_data')
    def test_constant_signal_exposed(self):
        r=self.compare([event('x',{'a':[1]*5,'b':[1,2,3,4,5]},
                              {'a':[1]*5,'b':[1,2,3,4,5]})])
        excluded=r['candidates'][0]['sides']['before']['excluded_signals']
        self.assertTrue(any(e['column']=='a' and e['reason']=='constant_signal' for e in excluded))
    def test_incompatible_bins_not_falsely_compared(self):
        x=event('x',{'a':[1,2,3,4,5]}, {'a':[1,2,3,4,5]})
        x['before']['alignment']['bin_count']=4
        x['before']['series']['a']=[1,2,3,4]
        r=self.compare([x])
        self.assertIsNone(r['candidates'][0]['full_context_similarity'])
        self.assertEqual(r['candidates'][0]['sides']['before']['excluded_signals'][0]['reason'],'incompatible_alignment')
    def test_incompatible_alignment_type(self):
        x=event('x',{'a':[1,2,3,4,5]}, {'a':[1,2,3,4,5]},method='elapsed_time_bins')
        x['before']['alignment']['bin_width_seconds']=10
        x['after']['alignment']['bin_width_seconds']=10
        r=self.compare([x])
        self.assertEqual(r['candidates'][0]['status'],'partial_evidence')
    def test_invalid_event_id(self):
        with self.assertRaises(ValueError): self.compare([self.target])
    def test_duplicate_candidate_id(self):
        x=event('x',{'a':[1,2,3,4,5]}, {'a':[1,2,3,4,5]})
        with self.assertRaises(ValueError): self.compare([x,x])
    def test_invalid_signal_selection(self):
        with self.assertRaises(ValueError): compare_event_contexts(self.target,[],selected_columns=['a','a'])
    def test_invalid_threshold(self):
        with self.assertRaises(ValueError): self.compare([],minimum_coverage=0)
    def test_candidate_limit(self):
        x=event('x',{'a':[1,2,3,4,5]}, {'a':[1,2,3,4,5]})
        with self.assertRaises(ValueError): self.compare([x],max_candidates=0)
    def test_no_mutation(self):
        import copy
        x=event('x',{'a':[1,2,3,4,5]}, {'a':[2,3,4,5,6]})
        t0=copy.deepcopy(self.target); x0=copy.deepcopy(x)
        self.compare([x])
        self.assertEqual(self.target,t0);self.assertEqual(x,x0)
    def test_stable_rank(self):
        good=event('good',{'a':[1,2,3,4,5],'b':[5,4,3,2,1]}, {'a':[2,3,4,5,6],'b':[1,2,3,4,5]})
        bad=event('bad',{'a':[5,4,3,2,1],'b':[1,2,3,4,5]}, {'a':[6,5,4,3,2],'b':[5,4,3,2,1]})
        r=self.compare([bad,good])
        self.assertEqual(r['candidates'][0]['candidate_id'],'good')
if __name__=='__main__': unittest.main()
