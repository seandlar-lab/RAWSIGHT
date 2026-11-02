import unittest
from rawsight.quality_evidence import assess_quality


class QualityEvidenceTests(unittest.TestCase):
    def test_default_whole_no_calendar(self):
        data = [{'x': 1}, {'x': 2}]
        result = assess_quality(data)
        self.assertEqual(result['regions'][0]['region']['kind'], 'whole')
        self.assertEqual(result['regions'][0]['row_count'], 2)

    def test_positive_and_attention_coexist(self):
        data = [{'time': '2020-01-01T00:00:00', 'good': 1, 'missing': 3},
                {'time': '2020-01-01T00:00:00', 'good': 2, 'missing': None}]
        f = assess_quality(data, time_column='time')['findings']
        self.assertIn('positive', [v['polarity'] for v in f])
        self.assertIn('attention', [v['polarity'] for v in f])
        repeat = next(v for v in f if v['kind'] == 'repeated_timestamps')
        self.assertEqual(repeat['evidence']['extra_rows_beyond_unique_timestamps'], 1)

    def test_row_ranges_half_open(self):
        data = [{'x': 1}, {'x': None}, {'x': 3}]
        result = assess_quality(data, regions=[{'id':'first','kind':'row_range','start':0,'stop':1},
                                                {'id':'rest','kind':'row_range','start':1,'stop':3}])
        self.assertEqual([r['row_count'] for r in result['regions']], [1,2])
        self.assertNotIn('missing_values', [f['kind'] for f in result['regions'][0]['findings']])
        self.assertIn('missing_values', [f['kind'] for f in result['regions'][1]['findings']])

    def test_category_regions(self):
        rows = [{'sector':'east','x':3}, {'sector':'west','x':None}, {'sector':'east','x':5}]
        r = assess_quality(rows, regions=[{'id':'east','kind':'category','column':'sector','value':'east'}])
        self.assertEqual(r['regions'][0]['row_count'], 2)
        self.assertNotIn('missing_values', [f['kind'] for f in r['findings']])

    def test_time_region_is_not_calendar(self):
        rows = [{'t':'2020-04-01T02:00:00','v':1}, {'t':'2020-04-01T03:00:00','v':2},
                {'t':'2020-04-01T04:00:00','v':None}]
        r = assess_quality(rows, time_column='t', regions=[
            {'id':'chosen','kind':'time_range','start':'2020-04-01T02:30:00','end':'2020-04-01T04:00:00'}])
        self.assertEqual(r['regions'][0]['row_count'], 1)

    def test_stable_cadence_and_variable_cadence(self):
        steady = [{'t':f'2020-01-01T0{i}:00:00'} for i in range(4)]
        kinds = [f['kind'] for f in assess_quality(steady, time_column='t')['findings']]
        self.assertIn('stable_observed_cadence', kinds)
        steady[-1] = {'t':'2020-01-01T05:00:00'}
        kinds = [f['kind'] for f in assess_quality(steady, time_column='t')['findings']]
        self.assertIn('variable_observed_cadence', kinds)

    def test_empty_and_invalid_timestamps(self):
        result = assess_quality([{'t': 'bad'}, {'t': None}], time_column='t')
        kinds = [f['kind'] for f in result['findings']]
        self.assertIn('invalid_timestamps', kinds)
        empty = assess_quality([], regions=[{'id':'none','kind':'whole'}])
        self.assertIn('empty_region', [f['kind'] for f in empty['findings']])

    def test_input_immutable(self):
        data = [{'t': '2020-01-01T00:00:00', 'v': 1}, {'t': '2020-01-01T01:00:00', 'v': 2}]
        copy = [dict(x) for x in data]
        assess_quality(data, time_column='t')
        self.assertEqual(data, copy)

    def test_validation(self):
        with self.assertRaises(ValueError):
            assess_quality([{'x':1}], regions=[{'id':'a','kind':'whole'}, {'id':'a','kind':'whole'}])
        with self.assertRaises(ValueError):
            assess_quality([{'x':1}], regions=[{'id':'x','kind':'row_range','start':1,'stop':2}])
        with self.assertRaises(ValueError):
            assess_quality([{'x':1}], regions=[{'id':'t','kind':'time_range','start':'2020-01-01','end':'2020-01-02'}])

    def test_out_of_order(self):
        data = [{'t':'2020-01-02T00:00:00'}, {'t':'2020-01-01T00:00:00'}]
        kinds = [f['kind'] for f in assess_quality(data,time_column='t')['findings']]
        self.assertIn('out_of_order', kinds)


if __name__ == '__main__':
    unittest.main()
