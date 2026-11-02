import json
import tempfile
import unittest
from pathlib import Path
from rawsight.dataset_profile_store import get_or_create_profile


class DatasetProfileStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'values.csv'
        self.source.write_text('a,b\n1,2\n', encoding='utf-8')
        self.store = self.root / 'profiles'
        self.calls = 0

    def profiler(self, path):
        self.calls += 1
        return {'rows': 1, 'columns': [{'name': 'a'}]}

    def run_profile(self, **kwargs):
        return get_or_create_profile(str(self.source), str(self.store), self.profiler, **kwargs)

    def test_created_then_reused(self):
        first = self.run_profile()
        second = self.run_profile()
        self.assertEqual('created', first['cache_status'])
        self.assertEqual('reused', second['cache_status'])
        self.assertEqual(1, self.calls)

    def test_profile_is_readable_json(self):
        result = self.run_profile()
        saved = json.loads(Path(result['profile_path']).read_text('utf-8'))
        self.assertEqual(1, saved['light_analysis']['rows'])

    def test_source_change_invalidates(self):
        self.run_profile()
        self.source.write_text('a,b\n1,2\n3,4\n', encoding='utf-8')
        self.assertEqual('created', self.run_profile()['cache_status'])
        self.assertEqual(2, self.calls)

    def test_version_change_invalidates(self):
        self.run_profile()
        self.assertEqual('created', self.run_profile(analysis_version='new')['cache_status'])
        self.assertEqual(2, self.calls)

    def test_metadata_separate_and_invalidates(self):
        metadata = self.root / 'metadata.json'
        metadata.write_text('{"a":"Temperature"}', encoding='utf-8')
        first = self.run_profile(metadata_path=str(metadata))
        self.assertEqual({'a': 'Temperature'}, first['dataset_profile']['external_metadata'])
        self.assertNotIn('Temperature', json.dumps(first['dataset_profile']['light_analysis']))
        self.assertEqual('reused', self.run_profile(metadata_path=str(metadata))['cache_status'])
        metadata.write_text('{"a":"Pressure"}', encoding='utf-8')
        self.assertEqual('created', self.run_profile(metadata_path=str(metadata))['cache_status'])

    def test_force_refresh(self):
        self.run_profile()
        self.assertEqual('refreshed', self.run_profile(force=True)['cache_status'])
        self.assertEqual(2, self.calls)

    def test_corrupt_cache_rebuilds(self):
        first = self.run_profile()
        Path(first['profile_path']).write_text('{broken', encoding='utf-8')
        self.assertEqual('created', self.run_profile()['cache_status'])
        self.assertEqual(2, self.calls)

    def test_no_source_copy(self):
        self.run_profile()
        self.assertEqual(1, len(list(self.store.iterdir())))
        self.assertFalse((self.store / self.source.name).exists())

    def test_invalid_metadata_rejected(self):
        metadata = self.root / 'metadata.json'
        metadata.write_text('[1,2]', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.run_profile(metadata_path=str(metadata))
        self.assertEqual(0, self.calls)

    def test_profiler_failure_no_cache(self):
        def fail(_):
            raise RuntimeError('failed')
        with self.assertRaises(RuntimeError):
            get_or_create_profile(str(self.source), str(self.store), fail)
        self.assertFalse(self.store.exists())

    def test_missing_source(self):
        with self.assertRaises(FileNotFoundError):
            get_or_create_profile(str(self.root/'missing.csv'), str(self.store), self.profiler)

    def test_non_json_metadata_rejected(self):
        metadata = self.root / 'metadata.xml'
        metadata.write_text('<x />', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.run_profile(metadata_path=str(metadata))

    def test_repeated_metadata_omission_is_reused(self):
        self.run_profile()
        self.assertEqual('reused', self.run_profile()['cache_status'])


if __name__ == '__main__':
    unittest.main()
