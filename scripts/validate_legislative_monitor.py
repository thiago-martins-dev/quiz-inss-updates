import argparse
from legislative_monitor import ROOT, load_json, official_https


def main(require_dependencies=False):
    required = ["sources/tracked_norms.json", "sources/source_registry.json", "state/monitored_norms.json", "state/last_run.json", "impact/legal_dependencies.json", "impact/latest_report.json", "impact/legal_dependencies.schema.json"]
    for relative in required: load_json(ROOT / relative)
    registry = load_json(ROOT / "sources/source_registry.json")
    for source in registry["sources"]:
        if source["enabled"] and not official_https(source["baseUrl"]): raise ValueError(f"Fonte inválida: {source['id']}")
    tracked = load_json(ROOT / "sources/tracked_norms.json")
    if len([x for x in tracked["norms"] if x["active"]]) != 4: raise ValueError("Catálogo deve iniciar com quatro normas ativas")
    deps = load_json(ROOT / "impact/legal_dependencies.json")
    if require_dependencies:
        if deps["productionQuestionCount"] != 707 or deps["uniqueIdCount"] != 707 or deps["duplicateIdCount"] != 0: raise ValueError("Contagem de questões inválida")
        if not deps["dependencies"] or deps["statistics"]["explicit"] == 0: raise ValueError("Índice sem vínculos explícitos")
        if len(deps["dependencies"]) + len(deps["unresolved"]) != 707: raise ValueError("Índice não cobre as 707 questões")
    print("Monitor legislativo válido.")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--require-dependencies", action="store_true"); args=parser.parse_args(); main(args.require_dependencies)
