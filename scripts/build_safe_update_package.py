import json
from legislative_monitor import ROOT, build_candidate, load_json, write_json

report = load_json(ROOT / "impact" / "latest_report.json")
if report["status"] != "safe_candidate":
    raise SystemExit("Nenhum candidato seguro a gerar")
package = build_candidate(report["impacts"], f"legal-{report['runId']}", "0.1.0")
if package is None: raise SystemExit("Nenhuma mudança real")
write_json(ROOT / "candidate-package.json", package)
print(json.dumps(package, ensure_ascii=False))
