"""Gera, valida e publica pacotes jurídicos declarativos de forma transacional."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from legislative_monitor import ROOT, official_https

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
SHA = re.compile(r"^[a-f0-9]{64}$")
ALLOWED_PAYLOAD = {"aptaParaEstudoAtual", "legislacaoDesatualizada", "motivoInaptidao", "avisoLegislativo", "referenciaLegalAtual", "dataAlteracaoLegal", "metadataNormativa"}
PROTECTED = {"id", "enunciado", "alternativas", "resposta", "gabaritoOficial", "explicacaoOficial", "banca", "concurso", "orgao", "cargo", "ano", "caderno", "origem", "anulada"}
FORBIDDEN_KEYS = {"script", "scripts", "command", "commands", "localPath", "binary", "executable", "apk", "dart", "javascript"}
EXPECTED_FIELDS = {"activeForCurrentStudy", "legislationStatus", "metadataVersion", "sourceHash"}
VOLATILE_FIELDS = {"startedAt", "finishedAt", "lastCheckedAt", "runId", "collectedAt"}


def canonical(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def https_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def bump_patch(version: str) -> str:
    match = SEMVER.fullmatch(version)
    if not match:
        raise ValueError("Versão deve usar X.Y.Z")
    major, minor, patch = map(int, match.groups())
    return f"{major}.{minor}.{patch + 1}"


def semantic(value):
    if isinstance(value, dict):
        return {key: semantic(item) for key, item in value.items() if key not in VOLATILE_FIELDS}
    if isinstance(value, list):
        return [semantic(item) for item in value]
    return value


def has_persistable_change(before, after) -> bool:
    return semantic(before) != semantic(after)


def validate_declarative(value) -> None:
    if isinstance(value, dict):
        if set(value) & FORBIDDEN_KEYS:
            raise ValueError("Conteúdo executável ou local proibido")
        for item in value.values(): validate_declarative(item)
    elif isinstance(value, list):
        for item in value: validate_declarative(item)
    elif isinstance(value, str):
        lowered = value.casefold()
        if re.search(r"(?:[a-z]:\\|javascript:|\.apk\b|\.exe\b|\.dart\b|\.js\b)", lowered):
            raise ValueError("Caminho, código ou binário proibido")


def logical_key(impact: dict) -> str:
    fields = [impact.get(key) for key in ("normId", "device", "oldHash", "changeHash", "suggestedAction", "contentId")]
    return digest(canonical(fields))


def build_package(report: dict, manifest: dict) -> dict:
    impacts = report.get("impacts", [])
    if report.get("status") != "safe_candidate" or not impacts:
        raise ValueError("Pacote exige impactos SAFE_AUTOMATIC")
    if any(item.get("risk") != "SAFE_AUTOMATIC" for item in impacts):
        raise ValueError("Impacto não seguro")
    version_from = manifest["contentVersion"]
    version_to = bump_patch(version_from)
    operations = []
    for item in sorted(impacts, key=logical_key):
        key = logical_key(item)
        payload = {"aptaParaEstudoAtual": False, "legislacaoDesatualizada": True, "motivoInaptidao": "Alteração legislativa detectada", "referenciaLegalAtual": {"normId": item["normId"], "device": item["device"], "changeHash": item["changeHash"]}, "dataAlteracaoLegal": item["detectedAt"]}
        operations.append({"operationId": f"op-{key[:24]}", "action": "deactivate", "entity": "question", "id": item["contentId"], "expectedCurrentState": {"activeForCurrentStudy": True, "legislationStatus": "current", "sourceHash": item.get("oldHash")}, "payload": payload, "preserveHistory": True, "idempotencyKey": key, "legalBasis": {"normId": item["normId"], "device": item["device"], "officialUrl": item["officialSource"], "changeHash": item["changeHash"]}, "detectedAt": item["detectedAt"], "effectiveAt": item.get("effectiveAt")})
    source_rows = {}
    for item in impacts:
        row = source_rows.setdefault(item["normId"], {"normId": item["normId"], "officialUrl": item["officialSource"], "collectedAt": item["detectedAt"], "documentSha256": item["documentSha256"], "affectedDevices": set()})
        row["affectedDevices"].add(item["device"])
    sources = [{**row, "affectedDevices": sorted(row["affectedDevices"])} for row in sorted(source_rows.values(), key=lambda x: x["normId"])]
    operations_hash = digest(canonical(operations))
    package_id = "legal-" + digest(canonical([logical_key(x) for x in impacts]))[:32]
    package = {"schemaVersion": 1, "packageId": package_id, "packageType": "legal-content", "packageVersion": version_to, "contentVersionFrom": version_from, "contentVersionTo": version_to, "createdAt": min(x["detectedAt"] for x in impacts), "minimumAppVersion": manifest["minimumAppVersion"], "sourceMonitorCommit": report["sourceCommit"], "sources": sources, "operations": operations, "integrity": {"algorithm": "SHA-256", "operationsSha256": operations_hash}}
    validate_package(package)
    return package


def validate_package(package: dict) -> None:
    if not package.get("operations") or package.get("packageType") != "legal-content":
        raise ValueError("Pacote vazio ou tipo inválido")
    if package["contentVersionTo"] != bump_patch(package["contentVersionFrom"]):
        raise ValueError("Incremento deve ser patch")
    keys, operation_ids = set(), set()
    for source in package["sources"]:
        if not official_https(source["officialUrl"]) or not SHA.fullmatch(source["documentSha256"]):
            raise ValueError("Fonte ou hash inválido")
    for operation in package["operations"]:
        if operation["action"] not in ("update", "deactivate") or operation["entity"] not in ("question", "legislation", "summaryMetadata") or not operation["preserveHistory"]:
            raise ValueError("Operação inválida")
        if set(operation["payload"]) & PROTECTED or not set(operation["payload"]) <= ALLOWED_PAYLOAD:
            raise ValueError("Campo protegido ou não permitido")
        if not set(operation["expectedCurrentState"]) <= EXPECTED_FIELDS:
            raise ValueError("Pré-condição não permitida")
        validate_declarative(operation["expectedCurrentState"]); validate_declarative(operation["payload"])
        if not official_https(operation["legalBasis"].get("officialUrl", "")):
            raise ValueError("Base legal não oficial")
        if "gabarito" in json.dumps(operation["expectedCurrentState"], ensure_ascii=False).casefold():
            raise ValueError("Pré-condição contém gabarito")
        if operation["idempotencyKey"] in keys:
            raise ValueError("Chave idempotente duplicada")
        if operation["operationId"] in operation_ids:
            raise ValueError("operationId duplicado")
        keys.add(operation["idempotencyKey"])
        operation_ids.add(operation["operationId"])
    if package["integrity"]["operationsSha256"] != digest(canonical(package["operations"])):
        raise ValueError("Integridade lógica inválida")


def manifest_with_package(manifest: dict, package: dict, url: str, file_hash: str, size: int) -> dict:
    if not https_url(url) or size <= 0 or not SHA.fullmatch(file_hash):
        raise ValueError("Asset não verificável")
    result = copy.deepcopy(manifest)
    if any(p["id"] == package["packageId"] or p["version"] == package["packageVersion"] for p in result["packages"]):
        raise ValueError("Pacote duplicado")
    result["contentVersion"] = package["contentVersionTo"]
    result["publishedAt"] = package["createdAt"]
    result["packages"].append({"id": package["packageId"], "type": "legal-content", "version": package["packageVersion"], "url": url, "sha256": file_hash, "sizeBytes": size, "compression": "none", "required": False, "description": "Atualização legislativa segura com preservação histórica."})
    result["packages"] = sorted(result["packages"], key=lambda x: tuple(map(int, x["version"].split("."))))[-10:]
    result["message"]["pt-BR"] = f"Conteúdo legislativo atualizado para {package['packageVersion']}."
    return result


def run_dry_run(fixture: Path) -> dict:
    original = (ROOT / "manifest.json").read_bytes()
    report = json.loads(fixture.read_text(encoding="utf-8"))
    manifest = json.loads(original.decode("utf-8-sig"))
    package = build_package(report, manifest)
    raw = canonical(package)
    file_hash, size = digest(raw), len(raw)
    simulated_url = f"https://github.com/thiago-martins-dev/quiz-inss-updates/releases/download/content-v{package['packageVersion']}/quiz-inss-content-{package['packageVersion']}.json"
    simulated = manifest_with_package(manifest, package, simulated_url, file_hash, size)
    if (ROOT / "manifest.json").read_bytes() != original:
        raise RuntimeError("Dry-run alterou o manifesto real")
    return {"dryRun": True, "releaseCreated": False, "packageVersion": package["packageVersion"], "operations": len(package["operations"]), "sha256": file_hash, "sizeBytes": size, "simulatedManifestVersion": simulated["contentVersion"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args()
    if args.dry_run:
        if not args.fixture: raise SystemExit("--fixture é obrigatório")
        print(json.dumps(run_dry_run(args.fixture), ensure_ascii=False, sort_keys=True)); return 0
    raise SystemExit("Publicação real é orquestrada exclusivamente pelo workflow")


if __name__ == "__main__":
    raise SystemExit(main())
