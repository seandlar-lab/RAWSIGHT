import unittest

from rawsight.pattern_similarity import compare_episodes


class PatternSimilarityTests(unittest.TestCase):
    def setUp(self):
        self.target = {'id':'reference', 'series': {
            'pressure': [1,2,3,4,5],
            'temperature': [10,12,14,16,18],
            'status': [1,1,1,1,1],
        }}

    def test_ranks_matching_shape_above_reversed(self):
        result = compare_episodes(self.target, [
            {'id':'reverse', 'series':{'pressure':[5,4,3,2,1], 'temperature':[18,16,14,12,10]}},
            {'id':'match', 'series':{'pressure':[11,12,13,14,15], 'temperature':[20,22,24,26,28]}},
        ])
        self.assertEqual(result['candidates'][0]['candidate_id'], 'match')
        self.assertAlmostEqual(result['candidates'][0]['shape_similarity'],1.0)
        self.assertGreater(result['candidates'][0]['signals'][0]['level_difference'],0)

    def test_constant_signals_not_scored(self):
        result = compare_episodes(self.target, [{'id':'x','series':{'status':[1,1,1,1,1]}}], selected_columns=['status'])
        self.assertEqual(result['status'], 'insufficient_data')
        self.assertEqual(result['candidates'][0]['excluded_signals'][-1]['reason'], 'constant_signal')

    def test_no_imputation_and_coverage(self):
        result = compare_episodes(self.target, [{'id':'x','series':{'pressure':[1,None,3,4,5]}}])
        self.assertEqual(result['status'], 'insufficient_data')
        result2 = compare_episodes(self.target, [{'id':'x','series':{'pressure':[1,None,3,4,5]}}], minimum_coverage=.8)
        self.assertEqual(result2['status'],'measured')
        self.assertEqual(result2['candidates'][0]['signals'][0]['paired_bins'],4)

    def test_mismatched_lengths(self):
        result = compare_episodes(self.target,[{'id':'bad','series':{'pressure':[1,2,3]}}])
        self.assertEqual(result['status'],'insufficient_data')

    def test_rejects_bad_parameters(self):
        with self.assertRaises(ValueError):
            compare_episodes(self.target, [], minimum_points=2)
        with self.assertRaises(ValueError):
            compare_episodes(self.target, [], minimum_coverage=0)


if __name__ == '__main__':
    unittest.main()
