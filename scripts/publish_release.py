"""Publica Release e só então atualiza o manifesto, com rollback da Release órfã."""
from __future__ import annotations

import json
import subprocess
import urllib.request
from pathlib import Path

from legislative_monitor import ROOT, load_json
from publish_safe_update import manifest_with_package


def run(*args, capture=False):
    return subprocess.run(args, cwd=ROOT, check=True, text=True, capture_output=capture)


def main() -> int:
    metadata = load_json(ROOT / "candidate-package.json")
    package_path = ROOT / metadata["path"]
    package = json.loads(package_path.read_text(encoding="utf-8"))
    manifest = load_json(ROOT / "manifest.json")
    version = metadata["version"]
    tag = f"content-v{version}"
    asset_url = f"https://github.com/thiago-martins-dev/quiz-inss-updates/releases/download/{tag}/{package_path.name}"
    if any(item["id"] == metadata["packageId"] for item in manifest["packages"]):
        print("Pacote já registrado; publicação idempotente."); return 0
    exists = subprocess.run(["gh", "release", "view", tag], cwd=ROOT, capture_output=True).returncode == 0
    if exists:
        raise RuntimeError(f"Tag {tag} já existe sem registro correspondente no manifesto")
    ids = ", ".join(str(op["id"]) for op in package["operations"])
    norms = ", ".join(source["normId"] for source in package["sources"])
    urls = "\n".join(f"- {source['officialUrl']}" for source in package["sources"])
    effective = ", ".join(sorted({op["effectiveAt"] or "não informada" for op in package["operations"]}))
    notes = f"Versão: {version}\nNormas: {norms}\nOperações: {len(package['operations'])}\nIDs afetados: {ids}\nFontes oficiais:\n{urls}\nSHA-256: {metadata['sha256']}\nTamanho: {metadata['sizeBytes']} bytes\nVigência: {effective}\nPreservação histórica obrigatória."
    created = False
    try:
        run("gh", "release", "create", tag, str(package_path), "--title", f"Quiz INSS Content {version}", "--notes", notes, "--latest=false")
        created = True
        request = urllib.request.Request(asset_url, method="HEAD", headers={"User-Agent": "TFM-Software-Quiz-INSS-Updater/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200: raise RuntimeError("Asset não está acessível")
        updated = manifest_with_package(manifest, package, asset_url, metadata["sha256"], metadata["sizeBytes"])
        (ROOT / "manifest.json").write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run("python", "scripts/validate_manifest.py")
        run("git", "add", "manifest.json", "snapshots", "state/monitored_norms.json")
        run("git", "commit", "-m", f"chore: publica conteúdo jurídico {version}")
        run("git", "push", "origin", "main")
        with urllib.request.urlopen("https://raw.githubusercontent.com/thiago-martins-dev/quiz-inss-updates/main/manifest.json", timeout=30) as response:
            if response.status != 200: raise RuntimeError("Manifesto remoto indisponível")
        return 0
    except Exception:
        if created:
            rollback = subprocess.run(["gh", "release", "delete", tag, "--yes", "--cleanup-tag"], cwd=ROOT)
            if rollback.returncode:
                subprocess.run(["gh", "issue", "create", "--title", f"Falha operacional na publicação {tag}", "--body", f"A Release órfã {tag} não pôde ser removida automaticamente. O manifesto não deve ser avançado."], cwd=ROOT)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
