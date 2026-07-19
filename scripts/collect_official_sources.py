"""Coleta fontes oficiais com retries limitados e cria baselines imutáveis."""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from legislative_monitor import MAX_BYTES, ROOT, USER_AGENT, load_json, normalize, official_https, sha256, split_devices, utc_now, write_json


def fetch(url: str, attempts: int = 3, timeout: int = 20, opener=urllib.request.urlopen) -> bytes:
    if not official_https(url): raise ValueError("blocked: URL deve ser HTTPS oficial")
    last = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xml,application/json,text/plain"})
            with opener(request, timeout=timeout) as response:
                final_url = response.geturl()
                if not official_https(final_url): raise ValueError("blocked: redirect não oficial ou sem HTTPS")
                data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES: raise ValueError("permanent: conteúdo excede 8 MiB")
                if not data.strip(): raise ValueError("temporary: resposta vazia")
                return data
        except urllib.error.HTTPError as error:
            if error.code in (401, 403): raise RuntimeError(f"authenticationRequired: HTTP {error.code}") from error
            if 400 <= error.code < 500: raise RuntimeError(f"permanent: HTTP {error.code}") from error
            last = error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last = error
        if attempt < attempts: time.sleep(min(2 ** (attempt - 1), 4))
    raise RuntimeError(f"temporary: falha após {attempts} tentativas: {last}")


def collect(opener=urllib.request.urlopen) -> dict:
    tracked = load_json(ROOT / "sources" / "tracked_norms.json")["norms"]
    state_path = ROOT / "state" / "monitored_norms.json"
    state = load_json(state_path)
    state.setdefault("norms", {})
    run = {"collectedAt": utc_now(), "norms": [], "errors": []}
    for norm in tracked:
        if not norm["active"]: continue
        try:
            raw = fetch(norm["url"], opener=opener)
            text = normalize(raw.decode("utf-8", "replace"))
            digest = sha256(text)
            devices = split_devices(text)
            folder = ROOT / "snapshots" / norm["id"]
            folder.mkdir(parents=True, exist_ok=True)
            previous_hash = state["norms"].get(norm["id"], {}).get("latestHash")
            snapshot_path = folder / f"{digest}.json"
            baseline = previous_hash is None
            if not snapshot_path.exists():
                write_json(snapshot_path, {"schemaVersion": 1, "normId": norm["id"], "sourceUrl": norm["url"], "primarySource": norm["primarySource"], "collectedAt": utc_now(), "sha256": digest, "devices": devices, "normalizedContent": text})
            state["norms"][norm["id"]] = {"latestHash": digest, "latestSnapshot": snapshot_path.relative_to(ROOT).as_posix(), "sourceUrl": norm["url"], "lastCheckedAt": utc_now()}
            run["norms"].append({"normId": norm["id"], "sourceUrl": norm["url"], "snapshot": snapshot_path.relative_to(ROOT).as_posix(), "currentHash": digest, "previousHash": previous_hash, "baselineCreated": baseline})
        except Exception as error:
            message = str(error)
            category = message.split(":", 1)[0] if ":" in message else "temporary"
            run["errors"].append({"normId": norm["id"], "category": category, "message": message})
    write_json(state_path, state)
    write_json(ROOT / "state" / "collection.json", run)
    return run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.parse_args()
    result = collect()
    print(json.dumps(result, ensure_ascii=False))
