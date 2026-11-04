"""Tests for the profile contract. Project integration uses actual DQ-COMP engine."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from rawsight.quality_requirements_profile_v1 import (
    PROFILE_SCHEMA, validate_profile, resolve_requirement,
    iter_profile_assessments, load_profile,
)

FP = 'a'*64


def profile(status='approved'):
    p = {
        'schema': PROFILE_SCHEMA,
        'profile_id': 'p1', 'profile_version': '0.1', 'status': status,
        'source': {'dataset_id': 'data1', 'sha256': FP},
        'requirements': [
            {'requirement_id': 'base', 'rule_id': 'DQ-COMP-001', 'rule_version': '0.1.0',
             'scope': 'dataset_column', 'column': 'TP3', 'max_missing': 0, 'source': 'contract-A'}
        ],
    }
    if status == 'approved':
        p['approved_by'] = 'reviewer'
        p['approved_at'] = '2026-11-04'
    return p


def resolve(p, area='r1', col='TP3', dataset='data1', sha=FP):
    return resolve_requirement(p, dataset_id=dataset, source_sha256=sha, area_id=area, column=col)


class RequirementsProfileTests(unittest.TestCase):
    def test_draft_does_not_assess(self):
        self.assertIsNone(resolve(profile('draft')))

    def test_approved_matches_all_areas_of_declared_column(self):
        p = profile()
        self.assertEqual(resolve(p, 'r1')['max_missing'], 0)
        self.assertEqual(resolve(p, 'r2')['max_missing'], 0)
        self.assertIsNone(resolve(p, 'r1', 'other'))

    def test_wrong_dataset_or_fingerprint_fails_closed(self):
        for kwargs in ({'dataset': 'other'}, {'sha': 'b'*64}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                resolve(profile(), **kwargs)

    def test_explicit_area_override(self):
        p = profile()
        p['requirements'].append({
            'requirement_id':'exception', 'rule_id':'DQ-COMP-001','rule_version':'0.1.0',
            'scope':'area_column','area_id':'r2','column':'TP3','max_missing':3,
            'source':'area-exception-approval','overrides':'base'})
        self.assertEqual(resolve(p,'r2')['max_missing'],3)
        self.assertEqual(resolve(p,'r1')['max_missing'],0)

    def test_implicit_override_forbidden(self):
        p=profile()
        p['requirements'].append({
            'requirement_id':'exception','rule_id':'DQ-COMP-001','rule_version':'0.1.0',
            'scope':'area_column','area_id':'r2','column':'TP3','max_missing':3,
            'source':'source'})
        with self.assertRaises(ValueError): validate_profile(p)

    def test_conflicting_rules_same_scope_forbidden(self):
        p=profile()
        x=copy.deepcopy(p['requirements'][0])
        x['requirement_id']='other';x['max_missing']=1
        p['requirements'].append(x)
        with self.assertRaises(ValueError):validate_profile(p)

    def test_missing_source_is_invalid(self):
        p=profile();p['requirements'][0]['source']=None
        with self.assertRaises(ValueError):validate_profile(p)

    def test_bool_limit_is_invalid(self):
        p=profile();p['requirements'][0]['max_missing']=True
        with self.assertRaises(ValueError):validate_profile(p)

    def test_unapproved_profile_cannot_approve_itself(self):
        p=profile();p.pop('approved_by')
        with self.assertRaises(ValueError):validate_profile(p)

    def test_validation_returns_copy(self):
        p=profile();v=validate_profile(p)
        v['requirements'][0]['max_missing']=19
        self.assertEqual(p['requirements'][0]['max_missing'],0)

    def test_load_profile_utf8(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'p.json';path.write_text(json.dumps(profile(),ensure_ascii=False),encoding='utf-8')
            self.assertEqual(load_profile(path)['profile_id'],'p1')

    def test_adapter_contract_and_no_file_modification(self):
        p=profile()
        record={'record_type':'finding','region_id':'r1','column':'TP3','kind':'complete_column',
                'evidence':{'rows':25,'missing':0},'interpretation_status':'observed'}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'e.jsonl'; content=json.dumps(record)+'\n';path.write_text(content,encoding='utf-8')
            result=list(iter_profile_assessments(path,p,dataset_id='data1',source_sha256=FP))
            self.assertEqual(result[0]['status'],'verified')
            self.assertEqual(result[0]['fact']['rows'],25)
            self.assertEqual(result[0]['evidence_ref']['line'],1)
            self.assertEqual(path.read_text(encoding='utf-8'),content)

    def test_stream_draft_yields_not_assessed(self):
        record={'record_type':'finding','region_id':'r1','column':'TP3','kind':'complete_column',
                'evidence':{'rows':2,'missing':0},'interpretation_status':'observed'}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'e.jsonl';path.write_text(json.dumps(record)+'\n',encoding='utf-8')
            r=list(iter_profile_assessments(path,profile('draft'),dataset_id='data1',source_sha256=FP))
            self.assertEqual(r[0]['status'],'not_assessed')

if __name__=='__main__':unittest.main()
