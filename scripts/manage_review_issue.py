"""Cria ou atualiza Issue usando marcador estável e GitHub CLI."""
import json, subprocess
from legislative_monitor import ROOT, load_json

report = load_json(ROOT / "impact" / "latest_report.json")
for impact in [x for x in report.get("impacts", []) if x["risk"] == "REVIEW_REQUIRED"]:
    marker = f"<!-- legal-monitor-key:{impact['issueKey']} -->"
    body = "\n".join([marker, "## Revisão legislativa necessária", f"- Norma: `{impact['normId']}`", f"- Dispositivo: `{impact['device']}`", f"- Classificação: `{impact['changeType']}`", f"- Fonte oficial: {impact['officialSource']}", f"- Conteúdos afetados: {', '.join(map(str, impact['affectedContentIds']))}", f"- Motivo: impacto requer revisão humana", f"- Data: {impact['detectedAt']}", f"- Hash: `{impact['changeHash']}`"])
    search = subprocess.run(["gh", "issue", "list", "--state", "open", "--search", f'\"{marker}\" in:body', "--json", "number", "--limit", "1"], cwd=ROOT, text=True, capture_output=True, check=True)
    issues = json.loads(search.stdout)
    if issues:
        subprocess.run(["gh", "issue", "edit", str(issues[0]["number"]), "--body", body], cwd=ROOT, check=True)
    else:
        subprocess.run(["gh", "issue", "create", "--title", f"Revisão legislativa: {impact['normId']} {impact['device']}", "--body", body], cwd=ROOT, check=True)
