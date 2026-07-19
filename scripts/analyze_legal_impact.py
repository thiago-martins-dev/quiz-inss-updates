import json, subprocess
from legislative_monitor import ROOT, classify_impact, load_json, sha256, stable_issue_key, utc_now, write_json


def analyze() -> dict:
    started = utc_now(); changes = load_json(ROOT / "impact" / "changes.json"); deps = load_json(ROOT / "impact" / "legal_dependencies.json"); collection = load_json(ROOT / "state" / "collection.json")
    collected_by_norm = {item["normId"]: item for item in collection["norms"]}
    by_norm = {}
    for dep in deps["dependencies"]: by_norm.setdefault(dep["normId"], []).append(dep)
    impacts = []
    for change in changes["changes"]:
        device_number = "".join(c for c in change["device"] if c.isdigit())
        affected = [d for d in by_norm.get(change["normId"], []) if not device_number or d["article"] == device_number]
        for dep in affected:
            current = collected_by_norm[change["normId"]]
            impact = {"normId": change["normId"], "device": change["device"], "changeType": change["changeType"], "contentId": dep["contentId"], "affectedContentIds": [dep["contentId"]], "referenceType": dep["referenceType"], "confidence": dep["confidence"], "suggestedAction": "deactivate_current_study", "officialSource": change["officialSource"], "detectedAt": utc_now(), "effectiveAt": None, "changes": {}, "oldHash": change.get("oldHash"), "changeHash": change.get("newHash") or change.get("oldHash"), "documentSha256": current["currentHash"]}
            impact["risk"] = classify_impact(impact); impact["issueKey"] = stable_issue_key(impact["normId"], impact["device"], impact["changeHash"] or "none")
            impacts.append(impact)
    status = "collection_failed" if collection["errors"] else "baseline_created" if changes["baselineCreated"] and not changes["changes"] else "no_changes" if not changes["changes"] else "blocked" if any(x["risk"] == "BLOCKED" for x in impacts) else "review_required" if any(x["risk"] == "REVIEW_REQUIRED" for x in impacts) else "safe_candidate"
    report = {"schemaVersion": 1, "runId": sha256(started)[:16], "startedAt": started, "finishedAt": utc_now(), "sourceCommit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "appSourceCommit": deps["sourceCommit"], "normsChecked": len(collection["norms"]), "dependenciesLoaded": len(deps["dependencies"]), "changesDetected": len(changes["changes"]), "impactsDetected": len(impacts), "status": status, "errors": collection["errors"], "artifacts": ["impact/changes.json"], "impacts": impacts}
    write_json(ROOT / "impact" / "latest_report.json", report); write_json(ROOT / "state" / "last_run.json", report); return report


if __name__ == "__main__": print(json.dumps(analyze(), ensure_ascii=False))
