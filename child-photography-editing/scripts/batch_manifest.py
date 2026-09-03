"""Create stable batch manifests and admit only fully passing items."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import PurePosixPath

REQUIRED_QA = ("identity", "childhood", "expression", "skin", "artifact", "theme", "batchConsistency")


def _lock_hash(batch_lock):
    try:
        canonical = json.dumps(batch_lock, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Batch Style Lock must be JSON serializable: {exc}") from exc
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _anchor_hash(source_id):
    canonical = json.dumps(source_id, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _assert_frozen_lock(manifest):
    expected = manifest.get("batchStyleLockHash")
    actual = _lock_hash(manifest.get("batchStyleLock"))
    if not expected or actual != expected:
        raise ValueError("Batch Style Lock was mutated after freezing")
    for item in manifest.get("items", []):
        if _lock_hash(item.get("batchStyleLock")) != expected:
            raise ValueError("Batch Style Lock snapshot was mutated after freezing")


def create_manifest(batch_id, batch_lock):
    frozen_lock = copy.deepcopy(batch_lock)
    return {
        "schemaVersion": "1.0",
        "batchId": batch_id,
        "batchStyleLock": frozen_lock,
        "batchStyleLockHash": _lock_hash(frozen_lock),
        "items": [],
        "anchorSourceId": None,
        "anchorSourceIdHash": None,
        "editedOutputs": [],
        "rejectedOutputs": [],
    }


def item_passes(item):
    qa = item.get("qa", {})
    return all(qa.get(key) == "pass" for key in REQUIRED_QA)


def record_item(manifest, item):
    _assert_frozen_lock(manifest)
    entry = copy.deepcopy(item)
    entry["batchStyleLock"] = copy.deepcopy(manifest["batchStyleLock"])
    if entry.get("candidateOutput") is None and entry.get("output") is not None:
        entry["candidateOutput"] = entry["output"]
    entry["status"] = "pending"
    manifest["items"].append(entry)
    return entry


def finalize_batch(manifest):
    _assert_frozen_lock(manifest)
    anchor_source_id = manifest.get("anchorSourceId")
    anchor_hash = manifest.get("anchorSourceIdHash")
    if anchor_source_id is None:
        if anchor_hash is not None:
            raise ValueError("anchor was mutated after selection")
    elif anchor_hash != _anchor_hash(anchor_source_id):
        raise ValueError("anchor was mutated after selection")
    if anchor_source_id is not None:
        matches = [item for item in manifest.get("items", []) if item.get("sourceId") == anchor_source_id]
        if len(matches) != 1 or not item_passes(matches[0]):
            raise ValueError(f"anchor {anchor_source_id!r} is missing or invalid")
    manifest["editedOutputs"] = []
    manifest["rejectedOutputs"] = []
    for item in manifest.get("items", []):
        candidate_output = item.get("candidateOutput", item.get("output"))
        if item_passes(item):
            item["status"] = "approved"
            if anchor_source_id is None:
                anchor_source_id = item.get("sourceId")
            if candidate_output:
                item["output"] = candidate_output
                item["deliveryPath"] = candidate_output
                manifest["editedOutputs"].append(candidate_output)
        else:
            item["status"] = "rejected"
            if candidate_output:
                item["candidateOutput"] = candidate_output
                filename = PurePosixPath(str(candidate_output).replace("\\", "/")).name
                rejected_output = f"rejected/{filename}"
                item["output"] = rejected_output
                item["deliveryPath"] = rejected_output
                manifest["rejectedOutputs"].append(rejected_output)
    manifest["anchorSourceId"] = anchor_source_id
    if anchor_source_id is not None and anchor_hash is None:
        manifest["anchorSourceIdHash"] = _anchor_hash(anchor_source_id)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or finalize a batch manifest")
    parser.add_argument("--batch-id", default="batch-1")
    parser.add_argument("--batch-lock", default="{}")
    args = parser.parse_args()
    try:
        manifest = create_manifest(args.batch_id, json.loads(args.batch_lock))
    except json.JSONDecodeError as exc:
        parser.error(f"invalid JSON: {exc.msg}")
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
