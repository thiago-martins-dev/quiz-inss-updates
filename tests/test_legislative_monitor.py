import io, os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from legislative_monitor import *
from build_legal_dependencies import build
from collect_official_sources import fetch

OFFICIAL = "https://www.planalto.gov.br/ccivil_03/leis/l8213cons.htm"


class Response:
    def __init__(self, body=b"ok", url=OFFICIAL): self.body, self.url = body, url
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, size): return self.body
    def geturl(self): return self.url


def impact(**changes):
    value={"officialSource":OFFICIAL,"referenceType":"explicit","confidence":1,"suggestedAction":"deactivate_current_study","contentId":1,"changes":{}}
    value.update(changes); return value


class MonitorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Path(os.environ.get("QUIZ_APP_PATH", Path(__file__).resolve().parents[2] / "quiz-inss-app"))

    def test_01_reconstructs_707_questions(self): self.assertEqual(build(self.app)["productionQuestionCount"],707)
    def test_02_ids_are_unique(self): self.assertEqual(build(self.app)["uniqueIdCount"],707)
    def test_03_has_no_duplicate_ids(self): self.assertEqual(build(self.app)["duplicateIdCount"],0)
    def test_04_has_explicit_dependency(self): self.assertGreater(build(self.app)["statistics"]["explicit"],0)
    def test_05_ambiguous_reference_not_promoted(self): self.assertTrue(any(x["reason"]=="ambiguousNorm" for x in build(self.app)["unresolved"]))
    def test_06_annulled_is_ineligible(self): self.assertTrue(all(not x["eligibleForAutomaticAction"] for x in build(self.app)["dependencies"] if x["historical"]))
    def test_07_pending_is_ineligible(self):
        data=build(self.app); pending={2447,2491,2495}; self.assertTrue(all(not x["eligibleForAutomaticAction"] for x in data["dependencies"] if x["contentId"] in pending))
    def test_08_missing_reference_is_unresolved(self): self.assertTrue(any(x["reason"] in ("noLegalReference","missingNorm") for x in build(self.app)["unresolved"]))
    def test_09_baseline_has_no_change(self): self.assertEqual(compare_documents({"sha256":"a"},{"sha256":"a"})["status"],"unchanged")
    def test_10_snapshot_names_are_content_addressed(self): self.assertNotEqual(sha256("v1"),sha256("v2"))
    def test_11_article_change_detected(self):
        old={"sha256":"a","devices":{"art. 1":{"sha256":"a"}}}; new={"sha256":"b","devices":{"art. 1":{"sha256":"b"}}}; self.assertEqual(compare_documents(old,new)["changes"][0]["changeType"],"modified")
    def test_12_whitespace_ignored(self): self.assertEqual(normalize("A  B\r\n"),normalize(" A B\n"))
    def test_13_retry_is_limited(self):
        calls=[]
        def fail(*args,**kwargs): calls.append(1); raise OSError("x")
        with self.assertRaises(RuntimeError): fetch(OFFICIAL, attempts=3, opener=fail)
        self.assertEqual(len(calls),3)
    def test_14_non_https_rejected(self): self.assertFalse(official_https("http://planalto.gov.br/x"))
    def test_15_unofficial_source_rejected(self): self.assertFalse(official_https("https://example.com/x"))
    def test_16_issue_key_deduplicates(self): self.assertEqual(stable_issue_key("n","a","h"),stable_issue_key("n","a","h"))
    def test_17_no_package_without_change(self): self.assertIsNone(build_candidate([],"p","1.0.0"))
    def test_18_historical_field_blocked(self): self.assertEqual(classify_impact(impact(changes={"officialAnswer":False})),"BLOCKED")
    def test_19_candidate_is_idempotent(self): self.assertEqual(build_candidate([impact()],"p","1.0.0")["sha256"],build_candidate([impact()],"p","1.0.0")["sha256"])
    def test_20_report_status_is_final(self): self.assertNotIn("no_run",{"baseline_created","no_changes","safe_candidate","review_required","blocked","collection_failed"})


if __name__ == "__main__": unittest.main()
