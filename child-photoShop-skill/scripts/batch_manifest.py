#!/usr/bin/env python3
"""Session manifest for batch retouch runs.

    batch_manifest.py init   <folder> [--session NAME] [--style NAME] [--out manifest.json]
    batch_manifest.py update <manifest> --image FILE [--status S] [--qa pass|fail]
                             [--output PATH] [--note TEXT]
    batch_manifest.py show   <manifest>

Every batch run needs an auditable record: which original, what was changed,
which backend, which parameters, which output file, and the QA verdict.  The
manifest is that record, and it is what makes a failed run recoverable instead
of mysterious.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from typing import Any, Dict, List, Sequence

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style_profile import IMAGE_EXT, collect_images  # noqa: E402

SCHEMA = "1.0"
STATUS_ORDER = ("pending", "analysed", "retouched", "qa_passed", "qa_failed", "delivered")


def now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def create_manifest(
    folder: str, session: str | None = None, style: str = "warm-studio-child"
) -> Dict[str, Any]:
    paths = collect_images(folder)
    session_name = session or os.path.basename(os.path.normpath(folder)) or "session"
    return {
        "schemaVersion": SCHEMA,
        "session": session_name,
        "created_at": now(),
        "updated_at": now(),
        "source_folder": os.path.abspath(folder),
        "style": style,
        "constraints": {
            "identity_lock": True,
            "childhood_preservation": True,
            "expression_preservation": True,
            "originals_preserved": True,
        },
        "images": [
            {
                "filename": os.path.basename(p),
                "path": p,
                "status": "pending",
                "qa": None,
                "output": None,
                "backend": None,
                "parameters": {},
                "notes": [],
            }
            for p in paths
        ],
        "selected": [],
        "status": "in_progress",
    }


def load_manifest(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_manifest(path: str, data: Dict[str, Any]) -> None:
    data["updated_at"] = now()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def update_image(
    data: Dict[str, Any],
    image: str,
    status: str | None = None,
    qa: str | None = None,
    output: str | None = None,
    backend: str | None = None,
    note: str | None = None,
) -> bool:
    base = os.path.basename(image)
    for entry in data.get("images", []):
        if entry["filename"] == base:
            if status:
                entry["status"] = status
            if qa:
                entry["qa"] = qa
                entry["status"] = "qa_passed" if qa == "pass" else "qa_failed"
            if output:
                entry["output"] = output
            if backend:
                entry["backend"] = backend
            if note:
                entry["notes"].append({"at": now(), "text": note})
            return True
    return False


def summary(data: Dict[str, Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for entry in data.get("images", []):
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    return counts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="batch_manifest.py", description="Create and update batch run manifests."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="create a manifest for a folder")
    p_init.add_argument("folder")
    p_init.add_argument("--session", help="session name (defaults to folder name)")
    p_init.add_argument("--style", default="warm-studio-child")
    p_init.add_argument("--out", default="manifest.json")
    p_init.set_defaults(func=_cmd_init)

    p_upd = sub.add_parser("update", help="update one image entry")
    p_upd.add_argument("manifest")
    p_upd.add_argument("--image", required=True)
    p_upd.add_argument("--status", choices=STATUS_ORDER)
    p_upd.add_argument("--qa", choices=["pass", "fail"])
    p_upd.add_argument("--output")
    p_upd.add_argument("--backend")
    p_upd.add_argument("--note")
    p_upd.set_defaults(func=_cmd_update)

    p_show = sub.add_parser("show", help="print a manifest summary")
    p_show.add_argument("manifest")
    p_show.set_defaults(func=_cmd_show)

    args = parser.parse_args(argv)
    return args.func(args)


def _cmd_init(args: argparse.Namespace) -> int:
    data = create_manifest(args.folder, args.session, args.style)
    save_manifest(args.out, data)
    print("created {} with {} image(s)".format(args.out, len(data["images"])))
    return 0


def _cmd_update(args: argparse.Namespace) -> int:
    data = load_manifest(args.manifest)
    if not update_image(data, args.image, args.status, args.qa,
                        args.output, args.backend, args.note):
        print("warning: {} not in manifest".format(args.image), file=sys.stderr)
        return 1
    save_manifest(args.manifest, data)
    print("updated {}".format(os.path.basename(args.image)))
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    data = load_manifest(args.manifest)
    print(json.dumps({
        "session": data["session"],
        "style": data["style"],
        "status": data["status"],
        "counts": summary(data),
        "selected": data.get("selected", []),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
