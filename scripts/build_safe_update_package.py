"""Gera o arquivo candidato determinístico; publicação ocorre em etapa posterior."""
import json
from pathlib import Path
from legislative_monitor import ROOT, load_json
from publish_safe_update import build_package, canonical, digest

report = load_json(ROOT / "impact/latest_report.json")
manifest = load_json(ROOT / "manifest.json")
package = build_package(report, manifest)
raw = canonical(package)
path = ROOT / f"quiz-inss-content-{package['packageVersion']}.json"
path.write_bytes(raw)
metadata = {"path": path.name, "sha256": digest(raw), "sizeBytes": len(raw), "packageId": package["packageId"], "version": package["packageVersion"]}
(ROOT / "candidate-package.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(metadata, ensure_ascii=False))
