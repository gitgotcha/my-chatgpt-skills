"""Create stable batch manifests and admit only fully passing items."""
from __future__ import annotations

import argparse
import copy
import json

REQUIRED_QA = ("identity", "childhood", "expression", "skin", "artifact", "theme", "batchConsistency")


def create_manifest(batch_id, batch_lock):
    return {"schemaVersion": "1.0", "batchId": batch_id, "batchStyleLock": copy.deepcopy(batch_lock), "items": [], "anchorSourceId": None, "editedOutputs": [], "rejectedOutputs": []}


def item_passes(item):
    qa = item.get("qa", {})
    return all(qa.get(key) == "pass" for key in REQUIRED_QA)


def record_item(manifest, item):
    entry = copy.deepcopy(item)
    entry["batchStyleLock"] = copy.deepcopy(manifest["batchStyleLock"])
    entry["status"] = "pending"
    manifest["items"].append(entry)
    return entry


def finalize_batch(manifest):
    manifest["anchorSourceId"] = None
    manifest["editedOutputs"] = []
    manifest["rejectedOutputs"] = []
    for item in manifest.get("items", []):
        if item_passes(item):
            item["status"] = "approved"
            if manifest["anchorSourceId"] is None:
                manifest["anchorSourceId"] = item.get("sourceId")
            if item.get("output"):
                manifest["editedOutputs"].append(item["output"])
        else:
            item["status"] = "rejected"
            if item.get("output"):
                manifest["rejectedOutputs"].append(item["output"])
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or finalize a batch manifest")
    parser.add_argument("--batch-id", default="batch-1")
    parser.add_argument("--batch-lock", default="{}")
    args = parser.parse_args()
    print(json.dumps(create_manifest(args.batch_id, json.loads(args.batch_lock)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
