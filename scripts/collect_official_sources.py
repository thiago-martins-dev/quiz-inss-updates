"""Coleta fontes oficiais com retries limitados e cria baselines imutáveis."""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from legislative_monitor import MAX_BYTES, ROOT, USER_AGENT, load_json, normalize, official_https, sha256, split_devices, utc_now, write_json

IDENTITY_MARKERS = {
    "br-cf-1988": "CONSTITUIÇÃO DA REPÚBLICA FEDERATIVA DO BRASIL",
    "br-lei-8212-1991": "LEI Nº 8.212, DE 24 DE JULHO DE 1991",
    "br-lei-8213-1991": "LEI Nº 8.213, DE 24 DE JULHO DE 1991",
    "br-decreto-3048-1999": "DECRETO Nº 3.048, DE 6 DE MAIO DE 1999",
}


class VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden_depth += 1
        elif tag in ("p", "div", "br", "li", "h1", "h2", "h3", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.hidden_depth:
            self.hidden_depth -= 1
        elif tag in ("p", "div", "li", "h1", "h2", "h3", "tr"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden_depth:
            self.parts.append(data)


def legal_text(raw: bytes, norm_id: str) -> str:
    parser = VisibleTextParser()
    parser.feed(raw.decode("utf-8", "replace"))
    text = normalize("".join(parser.parts))
    marker = IDENTITY_MARKERS[norm_id]
    identity_text = re.sub(r"\s+", " ", text).casefold()
    if marker.casefold() not in identity_text:
        raise ValueError(f"blocked: conteúdo não corresponde à norma {norm_id}")
    return text


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
            text = legal_text(raw, norm["id"])
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
