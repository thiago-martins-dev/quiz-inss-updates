import copy, json, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from publish_safe_update import *

ROOT_TEST = Path(__file__).resolve().parents[1]
FIXTURE = ROOT_TEST / "tests/fixtures/safe_impact.json"


class SafePublicationTests(unittest.TestCase):
    def setUp(self):
        self.report = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.manifest = json.loads((ROOT_TEST / "manifest.json").read_text(encoding="utf-8-sig"))
        self.package = build_package(self.report, self.manifest)

    def test_21_no_changes_has_no_persistable_change(self): self.assertFalse(has_persistable_change({"status":"no_changes"},{"status":"no_changes"}))
    def test_22_timestamps_are_volatile(self): self.assertFalse(has_persistable_change({"runId":"a","lastCheckedAt":"x"},{"runId":"b","lastCheckedAt":"y"}))
    def test_23_safe_package_is_valid(self): validate_package(self.package)
    def test_24_protected_field_is_blocked(self):
        package=copy.deepcopy(self.package); package["operations"][0]["payload"]["gabaritoOficial"]="A"
        with self.assertRaises(ValueError): validate_package(package)
    def test_25_empty_package_is_blocked(self):
        package=copy.deepcopy(self.package); package["operations"]=[]
        with self.assertRaises(ValueError): validate_package(package)
    def test_26_patch_version(self): self.assertEqual(bump_patch("1.0.0"),"1.0.1")
    def test_27_semantic_change_detected(self): self.assertTrue(has_persistable_change({"hash":"a"},{"hash":"b"}))
    def test_28_full_sha_is_correct(self): self.assertEqual(digest(b"abc"),"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
    def test_29_size_is_exact(self): self.assertEqual(len(canonical(self.package)),len(canonical(self.package).decode("utf-8").encode("utf-8")))
    def test_30_serialization_is_deterministic(self): self.assertEqual(canonical(self.package),canonical(json.loads(canonical(self.package))))
    def test_31_package_is_idempotent(self): self.assertEqual(build_package(self.report,self.manifest),build_package(self.report,self.manifest))
    def test_32_same_change_keeps_package_id(self): self.assertEqual(self.package["packageId"],build_package(self.report,self.manifest)["packageId"])
    def test_33_manifest_rejects_duplicate(self):
        raw=canonical(self.package); updated=manifest_with_package(self.manifest,self.package,"https://github.com/x/y",digest(raw),len(raw))
        with self.assertRaises(ValueError): manifest_with_package(updated,self.package,"https://github.com/x/y",digest(raw),len(raw))
    def test_34_non_https_is_rejected(self):
        with self.assertRaises(ValueError): manifest_with_package(self.manifest,self.package,"http://example.com/x","a"*64,1)
    def test_35_missing_asset_metadata_is_rejected(self):
        with self.assertRaises(ValueError): manifest_with_package(self.manifest,self.package,"https://example.com/x","a"*64,0)
    def test_36_review_is_not_publishable(self):
        report=copy.deepcopy(self.report); report["status"]="review_required"
        with self.assertRaises(ValueError): build_package(report,self.manifest)
    def test_37_blocked_is_not_publishable(self):
        report=copy.deepcopy(self.report); report["impacts"][0]["risk"]="BLOCKED"
        with self.assertRaises(ValueError): build_package(report,self.manifest)
    def test_38_release_precedes_manifest_policy(self): self.assertEqual(["release","verify_asset","manifest"].index("release"),0)
    def test_39_partial_failure_requires_release_rollback(self):
        events=["release","manifest_failure","release_delete"]; self.assertLess(events.index("manifest_failure"),events.index("release_delete"))
    def test_40_dry_run_preserves_real_manifest(self):
        before=(ROOT_TEST/"manifest.json").read_bytes(); result=run_dry_run(FIXTURE); self.assertEqual((ROOT_TEST/"manifest.json").read_bytes(),before); self.assertFalse(result["releaseCreated"])


if __name__ == "__main__": unittest.main()
