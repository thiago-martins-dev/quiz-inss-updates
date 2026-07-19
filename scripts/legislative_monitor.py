"""Núcleo seguro do Monitor Legislativo, somente com a biblioteca padrão."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 8 * 1024 * 1024
USER_AGENT = "TFM-Software-Quiz-INSS-Legislative-Monitor/1.0"
OFFICIAL_HOSTS = ("leg.br", "senado.leg.br", "camara.leg.br", "planalto.gov.br", "in.gov.br", "gov.br")
PROTECTED_FIELDS = {"id", "answer", "officialAnswer", "board", "exam", "agency", "role", "year", "booklet", "origin", "statement"}
ALLOWED_ACTIONS = {"mark_legislation_outdated", "deactivate_current_study", "preserve_history", "update_legislation_metadata", "update_effective_notice"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def official_https(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and any(host == item or host.endswith("." + item) for item in OFFICIAL_HOSTS)


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r">\s+<", "><", text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


DEVICE_RE = re.compile(r"(?im)(?=^\s*(?:Art\.?\s*\d+[A-Zº°-]*|§\s*\d+|[IVXLCDM]+\s*[-–—]|[a-z]\)))")


def split_devices(text: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for part in DEVICE_RE.split(normalize(text)):
        if not part.strip():
            continue
        match = re.match(r"\s*(Art\.?\s*\d+[A-Zº°-]*|§\s*\d+|[IVXLCDM]+\s*[-–—]|[a-z]\))", part, re.I)
        key = re.sub(r"\s+", " ", match.group(1)).lower() if match else "document"
        result[key] = {"text": part.strip(), "sha256": sha256(part.strip())}
    return result


def compare_documents(old: dict, new: dict) -> dict:
    if old["sha256"] == new["sha256"]:
        return {"status": "unchanged", "changes": []}
    before, after = old.get("devices", {}), new.get("devices", {})
    changes = []
    for key in sorted(before.keys() | after.keys()):
        if key not in before:
            kind = "added"
        elif key not in after:
            kind = "revoked"
        elif before[key]["sha256"] != after[key]["sha256"]:
            kind = "modified"
        else:
            continue
        changes.append({"device": key, "changeType": kind, "oldHash": before.get(key, {}).get("sha256"), "newHash": after.get(key, {}).get("sha256")})
    return {"status": "modified" if changes else "unchanged", "changes": changes}


def stable_issue_key(norm_id: str, device: str, change_hash: str) -> str:
    return sha256(f"{norm_id}|{device}|{change_hash}")[:24]


def classify_impact(impact: dict) -> str:
    if not official_https(impact.get("officialSource", "")):
        return "BLOCKED"
    if set(impact.get("changes", {})) & PROTECTED_FIELDS:
        return "BLOCKED"
    if impact.get("referenceType") != "explicit" or impact.get("confidence") != 1 or impact.get("suggestedAction") not in ALLOWED_ACTIONS:
        return "REVIEW_REQUIRED"
    return "SAFE_AUTOMATIC"


def build_candidate(impacts: list[dict], package_id: str, version: str) -> dict | None:
    if not impacts:
        return None
    if any(classify_impact(item) != "SAFE_AUTOMATIC" for item in impacts):
        raise ValueError("Pacote bloqueado por impacto não seguro")
    operations = [{"operation": item["suggestedAction"], "contentType": "question", "contentId": item["contentId"], "preserveHistory": True, "sourceUrl": item["officialSource"]} for item in impacts]
    canonical = json.dumps(operations, sort_keys=True, separators=(",", ":"))
    return {"packageId": package_id, "version": version, "candidateOnly": True, "operations": operations, "sha256": sha256(canonical), "impactReport": impacts}
