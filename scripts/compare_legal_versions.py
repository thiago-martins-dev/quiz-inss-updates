import json
from pathlib import Path
from legislative_monitor import ROOT, compare_documents, load_json, utc_now, write_json


def compare_collection() -> dict:
    collection = load_json(ROOT / "state" / "collection.json")
    result = {"generatedAt": utc_now(), "baselineCreated": [], "changes": [], "unchanged": []}
    for item in collection["norms"]:
        if item["baselineCreated"]:
            result["baselineCreated"].append(item["normId"]); continue
        if item["previousHash"] == item["currentHash"]:
            result["unchanged"].append(item["normId"]); continue
        folder = ROOT / "snapshots" / item["normId"]
        old = load_json(folder / f"{item['previousHash']}.json")
        new = load_json(ROOT / item["snapshot"])
        comparison = compare_documents(old, new)
        for change in comparison["changes"]:
            result["changes"].append({"normId": item["normId"], "officialSource": item["sourceUrl"], **change})
    write_json(ROOT / "impact" / "changes.json", result)
    return result


if __name__ == "__main__": print(json.dumps(compare_collection(), ensure_ascii=False))
