import os
from legislative_monitor import ROOT, load_json

report = load_json(ROOT / "impact" / "latest_report.json")
status = report["status"]
output = os.environ.get("GITHUB_OUTPUT")
if output:
    with open(output, "a", encoding="utf-8") as stream:
        stream.write(f"status={status}\n")
        keys = sorted({item["issueKey"] for item in report.get("impacts", []) if item["risk"] == "REVIEW_REQUIRED"})
        stream.write(f"review_keys={','.join(keys)}\n")
print(status)
if status in ("blocked", "collection_failed"):
    raise SystemExit(2)
