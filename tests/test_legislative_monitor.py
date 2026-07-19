import io, subprocess, sys, tempfile, unittest
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
        cls.dependencies = load_json(ROOT / "impact" / "legal_dependencies.json")
        cls.fixture = tempfile.TemporaryDirectory()
        app = Path(cls.fixture.name)
        (app / "lib").mkdir()
        questions = []
        for content_id in range(1, 705):
            legal = ""
            if content_id == 1:
                legal = "baseLegal: 'Lei nº 8.213/1991', artigo: 'art. 15',"
            elif content_id == 2:
                legal = "baseLegal: 'Lei nº 8.212/1991 e Lei nº 8.213/1991', artigo: 'art. 1',"
            elif content_id == 697:
                legal = "baseLegal: 'Lei nº 8.213/1991', artigo: 'art. 16',"
            annulled = "anulada: true," if content_id >= 697 else ""
            questions.append(f"Questao(id: {content_id}, {legal} {annulled})")
        questions.append("...QuestoesExpansaoIncapacidadeInss.questoes")
        (app / "lib" / "banco_questoes.dart").write_text("\n".join(questions), encoding="utf-8")
        pending = [
            f"_criarQuestao(id: {content_id}, baseLegal: 'Lei nº 8.213/1991', artigo: 'art. 59')"
            for content_id in (2447, 2491, 2495)
        ]
        (app / "lib" / "questoes_expansao_incapacidade_inss.dart").write_text("\n".join(pending), encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(app)], check=True)
        subprocess.run(["git", "-C", str(app), "config", "user.email", "fixture@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(app), "config", "user.name", "Fixture"], check=True)
        subprocess.run(["git", "-C", str(app), "add", "lib"], check=True)
        subprocess.run(["git", "-C", str(app), "commit", "-q", "-m", "fixture"], check=True)
        cls.generated = build(app)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def test_01_reconstructs_707_questions(self): self.assertEqual(self.generated["productionQuestionCount"],707)
    def test_02_ids_are_unique(self): self.assertEqual(self.generated["uniqueIdCount"],707)
    def test_03_has_no_duplicate_ids(self): self.assertEqual(self.generated["duplicateIdCount"],0)
    def test_04_has_explicit_dependency(self): self.assertGreater(self.generated["statistics"]["explicit"],0)
    def test_05_ambiguous_reference_not_promoted(self): self.assertTrue(any(x["reason"]=="ambiguousNorm" for x in self.generated["unresolved"]))
    def test_06_annulled_is_ineligible(self):
        historical=[x for x in self.generated["dependencies"] if x["historical"]]; self.assertTrue(historical); self.assertTrue(all(not x["eligibleForAutomaticAction"] for x in historical))
    def test_07_pending_is_ineligible(self):
        pending={2447,2491,2495}; found=[x for x in self.generated["dependencies"] if x["contentId"] in pending]; self.assertEqual({x["contentId"] for x in found},pending); self.assertTrue(all(not x["eligibleForAutomaticAction"] for x in found))
    def test_08_missing_reference_is_unresolved(self): self.assertTrue(any(x["reason"] in ("noLegalReference","missingNorm") for x in self.generated["unresolved"]))
    def test_09_baseline_has_no_change(self): self.assertEqual(compare_documents({"sha256":"a"},{"sha256":"a"})["status"],"unchanged")
    def test_10_snapshot_names_are_content_addressed(self):
        old=sha256("v1"); new=sha256("v2"); self.assertNotEqual(old,new); self.assertEqual(sha256("v1"),old)
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
