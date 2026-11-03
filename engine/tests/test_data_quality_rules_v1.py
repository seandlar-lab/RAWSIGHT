import copy
import json
import tempfile
import unittest
from pathlib import Path
from rawsight.data_quality_rules_v1 import assess_completeness, iter_completeness_assessments

F = {"record_type":"finding", "region_id":"region_000000149", "column":"TP3",
     "kind":"complete_column", "polarity":"positive", "evidence":{"rows":36597,"missing":0},
     "interpretation_status":"observed"}
R = {"rule_id":"DQ-COMP-001", "rule_version":"0.1.0", "column":"TP3",
     "area_id":"region_000000149", "max_missing":0, "source":"explicit-test-contract"}

class CompletenessRuleTests(unittest.TestCase):
    def test_no_requirement_is_not_assessed(self):
        r = assess_completeness(F)
        self.assertEqual(r["status"], "not_assessed")
        self.assertEqual(r["fact"]["missing"], 0)

    def test_explicit_requirement_verified(self):
        self.assertEqual(assess_completeness(F, R)["status"], "verified")

    def test_requirement_broken(self):
        f = copy.deepcopy(F); f["evidence"]["missing"] = 2
        self.assertEqual(assess_completeness(f, R)["status"], "violation")

    def test_tolerated_missing_count(self):
        f = copy.deepcopy(F); f["evidence"]["missing"] = 2
        r = dict(R, max_missing=2)
        self.assertEqual(assess_completeness(f, r)["status"], "verified")

    def test_missing_fact_is_insufficient(self):
        self.assertEqual(assess_completeness(None, R)["status"], "insufficient_evidence")

    def test_partial_fact_is_insufficient(self):
        f = copy.deepcopy(F); del f["evidence"]["missing"]
        self.assertEqual(assess_completeness(f, R)["status"], "insufficient_evidence")

    def test_requirement_without_source_rejected(self):
        with self.assertRaises(ValueError):
            assess_completeness(F, dict(R, source=""))

    def test_mismatched_scope_rejected(self):
        with self.assertRaises(ValueError):
            assess_completeness(F, dict(R, area_id="region_other"))

    def test_invalid_numbers_rejected(self):
        for bad in (True, -1, 1.1, "0"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                assess_completeness(F, dict(R, max_missing=bad))
        f=copy.deepcopy(F); f["evidence"]["missing"] = 40000
        with self.assertRaises(ValueError):
            assess_completeness(f, R)

    def test_fact_not_mutated_and_provenance(self):
        old=copy.deepcopy(F)
        ref={"path":"example.jsonl", "line":42}
        result=assess_completeness(F, R, evidence_ref=ref)
        self.assertEqual(F, old)
        self.assertEqual(result["evidence_ref"], ref)
        self.assertEqual(result["requirement"]["source"], "explicit-test-contract")

    def test_zero_rows_not_verified(self):
        f = copy.deepcopy(F); f["evidence"] = {"rows":0, "missing":0}
        self.assertEqual(assess_completeness(f, R)["status"], "insufficient_evidence")

    def test_missing_requirement_evidence_at_eof(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"empty.jsonl"
            p.write_text("", encoding="utf-8")
            a=list(iter_completeness_assessments(p,{(R["area_id"],R["column"]):R}))
            self.assertEqual(len(a),1)
            self.assertEqual(a[0]["status"],"insufficient_evidence")

    def test_streaming_jsonl_reads_only_supported_facts(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"facts.jsonl"
            lines=[{"record_type":"region", "id":F["region_id"]}, F,
                   {"record_type":"finding","kind":"time_structure","region_id":F["region_id"]}]
            p.write_text("\n".join(json.dumps(x) for x in lines)+"\n", encoding="utf-8")
            assessments=list(iter_completeness_assessments(p, {(R["area_id"], R["column"]): R}))
            self.assertEqual(len(assessments),1)
            self.assertEqual(assessments[0]["status"],"verified")
            self.assertEqual(assessments[0]["evidence_ref"]["line"],2)

if __name__ == "__main__": unittest.main()
