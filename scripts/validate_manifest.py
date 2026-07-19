#!/usr/bin/env python3
"""Valida o manifesto local sem rede nem dependências externas."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
SHA256 = re.compile(r"^[A-Fa-f0-9]{64}$")
ROOT_FIELDS = {
    "schemaVersion", "channel", "enabled", "contentVersion",
    "minimumAppVersion", "publishedAt", "checkIntervalHours",
    "packages", "message",
}
PACKAGE_FIELDS = {
    "id", "type", "version", "url", "sha256", "sizeBytes",
    "compression", "required", "description",
}


def fail(message: str) -> None:
    raise ValueError(message)


def require_type(value: object, expected: type, field: str) -> None:
    if type(value) is not expected:
        fail(f"'{field}' deve ser {expected.__name__}.")


def validate_semver(value: object, field: str) -> None:
    require_type(value, str, field)
    if not SEMVER.fullmatch(value):
        fail(f"'{field}' deve usar versão semântica X.Y.Z.")


def validate_datetime(value: object) -> None:
    require_type(value, str, "publishedAt")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        fail(f"'publishedAt' não é ISO-8601 válido: {error}")
    if parsed.tzinfo is None:
        fail("'publishedAt' deve incluir fuso horário.")


def validate_package(package: object, index: int) -> None:
    require_type(package, dict, f"packages[{index}]")
    missing = PACKAGE_FIELDS - package.keys()
    unknown = package.keys() - PACKAGE_FIELDS
    if missing:
        fail(f"packages[{index}] sem campos: {', '.join(sorted(missing))}.")
    if unknown:
        fail(f"packages[{index}] contém campos desconhecidos: {', '.join(sorted(unknown))}.")
    for field in ("id", "type", "description"):
        require_type(package[field], str, f"packages[{index}].{field}")
        if not package[field].strip():
            fail(f"packages[{index}].{field} não pode ser vazio.")
    validate_semver(package["version"], f"packages[{index}].version")
    require_type(package["url"], str, f"packages[{index}].url")
    parsed_url = urlparse(package["url"])
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        fail(f"packages[{index}].url deve ser HTTPS válida.")
    require_type(package["sha256"], str, f"packages[{index}].sha256")
    if not SHA256.fullmatch(package["sha256"]):
        fail(f"packages[{index}].sha256 deve conter 64 caracteres hexadecimais.")
    require_type(package["sizeBytes"], int, f"packages[{index}].sizeBytes")
    if package["sizeBytes"] <= 0:
        fail(f"packages[{index}].sizeBytes deve ser maior que zero.")
    require_type(package["required"], bool, f"packages[{index}].required")
    if package["compression"] not in {"none", "zip", "gzip"}:
        fail(f"packages[{index}].compression deve ser none, zip ou gzip.")


def validate(manifest: object) -> None:
    require_type(manifest, dict, "manifest")
    missing = ROOT_FIELDS - manifest.keys()
    unknown = manifest.keys() - ROOT_FIELDS
    if missing:
        fail(f"Campos obrigatórios ausentes: {', '.join(sorted(missing))}.")
    if unknown:
        fail(f"Campos desconhecidos: {', '.join(sorted(unknown))}.")
    require_type(manifest["schemaVersion"], int, "schemaVersion")
    if manifest["schemaVersion"] < 1:
        fail("'schemaVersion' deve ser maior ou igual a 1.")
    require_type(manifest["channel"], str, "channel")
    if not manifest["channel"].strip():
        fail("'channel' não pode ser vazio.")
    require_type(manifest["enabled"], bool, "enabled")
    validate_semver(manifest["contentVersion"], "contentVersion")
    validate_semver(manifest["minimumAppVersion"], "minimumAppVersion")
    validate_datetime(manifest["publishedAt"])
    require_type(manifest["checkIntervalHours"], int, "checkIntervalHours")
    if not 1 <= manifest["checkIntervalHours"] <= 168:
        fail("'checkIntervalHours' deve estar entre 1 e 168.")
    require_type(manifest["packages"], list, "packages")
    for index, package in enumerate(manifest["packages"]):
        validate_package(package, index)
    require_type(manifest["message"], dict, "message")
    if set(manifest["message"]) != {"pt-BR"}:
        fail("'message' deve conter somente o campo obrigatório 'pt-BR'.")
    require_type(manifest["message"]["pt-BR"], str, "message.pt-BR")
    if not manifest["message"]["pt-BR"].strip():
        fail("'message.pt-BR' não pode ser vazio.")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    path = root / "manifest.json"
    try:
        with path.open("r", encoding="utf-8") as manifest_file:
            manifest = json.load(manifest_file)
        validate(manifest)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Manifesto inválido: {error}", file=sys.stderr)
        return 1
    print(f"Manifesto válido: {path}")
    print(f"Versão de conteúdo: {manifest['contentVersion']}; pacotes: {len(manifest['packages'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
