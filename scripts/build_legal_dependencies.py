"""Reconstrói vínculos jurídicos usando apenas metadados das questões de produção."""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

from legislative_monitor import ROOT, load_json, utc_now, write_json

EXPECTED = {"production": 707, "unique": 707, "duplicates": 0, "eligible": 696, "annulled": 8, "pending": 3}
NORMS = {
    "br-cf-1988": (re.compile(r"Constitui(?:ção|cao)(?: Federal| da República Federativa do Brasil)", re.I),),
    "br-lei-8212-1991": (re.compile(r"Lei\s+n?[º°.]?\s*8\.212/1991", re.I),),
    "br-lei-8213-1991": (re.compile(r"Lei\s+n?[º°.]?\s*8\.213/1991", re.I),),
    "br-decreto-3048-1999": (re.compile(r"Decreto\s+n?[º°.]?\s*3\.048/1999", re.I),),
}


def balanced_calls(text: str, token: str):
    for match in re.finditer(rf"(?m)^\s*{re.escape(token)}\(", text):
        depth = 0
        for index in range(match.start(), len(text)):
            if text[index] == "(": depth += 1
            elif text[index] == ")":
                depth -= 1
                if depth == 0:
                    yield text[match.start():index + 1], text.count("\n", 0, match.start()) + 1
                    break


def field(block: str, name: str) -> str:
    match = re.search(rf"(?ms)^\s*{name}:\s*(?:r)?(?:'''(.*?)'''|'([^']*)')", block)
    return (match.group(1) or match.group(2) or "").strip() if match else ""


def production_files(app: Path) -> list[Path]:
    bank = app / "lib" / "banco_questoes.dart"
    text = bank.read_text(encoding="utf-8")
    names = re.findall(r"\.\.\.(Questoes\w+)\.questoes", text)
    imports = dict(re.findall(r"import '([^']+)';", text)) if False else None
    files = [bank]
    for class_name in names:
        snake = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()
        candidate = app / "lib" / f"{snake}.dart"
        if not candidate.exists():
            raise RuntimeError(f"Fonte concatenada ausente: {candidate}")
        files.append(candidate)
    return files


def build(app: Path) -> dict:
    tracked = {item["id"]: item for item in load_json(ROOT / "sources" / "tracked_norms.json")["norms"]}
    records = []
    approved_expansion = set()
    expansion = app / "lib" / "questoes_expansao_incapacidade_inss.dart"
    match = re.search(r"_idsAprovadosRevisaoFinal\s*=\s*\{(.*?)\};", expansion.read_text(encoding="utf-8"), re.S)
    if match: approved_expansion = {int(value) for value in re.findall(r"\b\d+\b", match.group(1))}
    for path in production_files(app):
        text = path.read_text(encoding="utf-8")
        token = "Questao" if path.name == "banco_questoes.dart" else "_criarQuestao"
        for block, line in balanced_calls(text, token):
            id_match = re.search(r"(?m)^\s*id:\s*(\d+),", block)
            if not id_match: continue
            content_id = int(id_match.group(1))
            annulled = bool(re.search(r"anulada:\s*true", block))
            pending = path.name == expansion.name and content_id not in approved_expansion
            base, article = field(block, "baseLegal"), field(block, "artigo")
            records.append({"id": content_id, "source": f"lib/{path.name}:{line}", "base": base, "article": article, "annulled": annulled, "pending": pending})
    ids = [item["id"] for item in records]
    duplicates = len(ids) - len(set(ids))
    eligible_count = sum(not item["annulled"] and not item["pending"] for item in records)
    observed = {"production": len(records), "unique": len(set(ids)), "duplicates": duplicates, "eligible": eligible_count, "annulled": sum(item["annulled"] for item in records), "pending": sum(item["pending"] for item in records)}
    if observed != EXPECTED:
        raise RuntimeError(f"Banco mudou: esperado={EXPECTED}; observado={observed}")
    dependencies, unresolved = [], []
    for item in records:
        combined = " | ".join(value for value in (item["base"], item["article"]) if value)
        matched = [norm_id for norm_id, patterns in NORMS.items() if any(pattern.search(combined) for pattern in patterns)]
        article_match = re.search(r"\bart\.?\s*([0-9]+[A-Z]?(?:[-–][A-Z])?)", combined, re.I)
        if len(matched) == 1 and article_match:
            norm_id = matched[0]
            historical = item["annulled"]
            dependencies.append({"contentType": "question", "contentId": item["id"], "normId": norm_id, "article": article_match.group(1), "paragraph": None, "item": None, "letter": None, "referenceType": "explicit", "confidence": 1.0, "sourceLocation": item["source"], "eligibleForAutomaticAction": bool(tracked[norm_id]["active"] and not item["annulled"] and not item["pending"]), "historical": historical, "activeForCurrentStudy": not item["annulled"] and not item["pending"]})
        else:
            reason = "missingNorm" if not matched else "ambiguousNorm" if len(matched) > 1 else "missingArticle"
            if not combined: reason = "noLegalReference"
            unresolved.append({"contentId": item["id"], "sourceLocation": item["source"], "reason": reason, "candidateReference": combined[:180] or None, "requiresReview": True})
    commit = subprocess.check_output(["git", "-C", str(app), "rev-parse", "HEAD"], text=True).strip()
    stats = {"explicit": len(dependencies), "extracted": 0, "inferred": 0, "eligible": sum(x["eligibleForAutomaticAction"] for x in dependencies), "historical": sum(x["historical"] for x in dependencies), "unresolved": len(unresolved)}
    return {"schemaVersion": 1, "generatedAt": utc_now(), "sourceRepository": "https://github.com/thiago-martins-dev/quiz-inss-app", "sourceCommit": commit, "productionQuestionCount": len(records), "uniqueIdCount": len(set(ids)), "duplicateIdCount": duplicates, "dependencies": dependencies, "unresolved": unresolved, "statistics": stats}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "impact" / "legal_dependencies.json")
    args = parser.parse_args()
    write_json(args.output, build(args.app.resolve()))
    print(f"Índice criado em {args.output}")
