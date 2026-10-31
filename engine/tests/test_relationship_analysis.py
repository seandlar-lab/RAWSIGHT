import unittest
import duckdb
from rawsight.relationship_analysis import execute_relationship_analysis


class FakeSourceContext:
    def __init__(self, con, names, types):
        self._con = con
        self.column_names = names
        self.column_types = types
        self.view_name = 'rawsight_source'
        self.is_open = True
    def assert_source(self, filename):
        if filename != 'synthetic':
            raise ValueError('wrong source')
    def require_connection(self):
        return self._con


class RelationshipTests(unittest.TestCase):
    def setUp(self):
        self.db = duckdb.connect(':memory:')
        self.db.execute('''CREATE VIEW rawsight_source AS SELECT * FROM (VALUES
            (1, 2, 8, 1, CAST(NULL AS DOUBLE)),
            (2, 4, 7, 1, 5.0),
            (3, 6, 6, 1, 6.0),
            (4, 8, 5, 1, 7.0),
            (5, 10, 4, 1, 8.0)
        ) AS t(a,b,c,d,e)''')
        self.context = FakeSourceContext(self.db, ['a','b','c','d','e'], ['INTEGER','INTEGER','INTEGER','INTEGER','DOUBLE'])
    def tearDown(self):
        self.db.close()
    def run_analysis(self, **kwargs):
        return execute_relationship_analysis(file_path='synthetic', source_context=self.context, **kwargs)
    def test_positive_and_negative_pairs(self):
        r = self.run_analysis(selected_columns=['a','b','c'])
        pairs = {(p['column_a'],p['column_b']):p for p in r['relationships']}
        self.assertAlmostEqual(pairs['a','b']['pearson_r'],1)
        self.assertAlmostEqual(pairs['a','c']['pearson_r'],-1)
        self.assertFalse(r['execution']['sampled'])
    def test_pairwise_missingness(self):
        r = self.run_analysis(selected_columns=['a','e'])
        self.assertEqual(r['row_count'],5)
        self.assertEqual(r['relationships'][0]['pair_count'],4)
        self.assertEqual(r['columns'][1]['missing_or_nonfinite_count'],1)
    def test_constant_pair(self):
        r = self.run_analysis(selected_columns=['a','d'])
        self.assertEqual(r['relationships'][0]['status'],'zero_pairwise_variance')
        self.assertIsNone(r['relationships'][0]['pearson_r'])
    def test_column_limit_no_implicit_subset(self):
        r = self.run_analysis(max_columns=2)
        self.assertEqual(r['status'],'resource_limit')
        self.assertEqual(r['relationships'],[])
    def test_reject_duplicate_and_unknown_columns(self):
        for names in (['a','a'],['a','unknown']):
            with self.assertRaises(ValueError):
                self.run_analysis(selected_columns=names)
    def test_insufficient_data(self):
        r = self.run_analysis(selected_columns=['a','e'], min_pair_observations=6)
        self.assertEqual(r['relationships'][0]['status'],'insufficient_data')
    def test_time_window_requires_axis(self):
        with self.assertRaises(ValueError):
            self.run_analysis(selected_columns=['a','b'],start_time='2020-01-01',end_time='2020-01-02')
    def test_empty_pair(self):
        self.db.execute('CREATE OR REPLACE VIEW rawsight_source AS SELECT NULL::DOUBLE AS a, NULL::DOUBLE AS b')
        self.context.column_names=['a','b'];self.context.column_types=['DOUBLE','DOUBLE']
        r=self.run_analysis()
        self.assertEqual(r['status'],'insufficient_data')
        self.assertEqual(r['relationships'][0]['pair_count'],0)

if __name__=='__main__':
    unittest.main()
