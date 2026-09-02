#!/usr/bin/env python3
"""Deterministic validator for generated profile-aware Skills.

Usage:

    python scripts/validate_profile_skill.py --mode plain <target-skill-dir>
    python scripts/validate_profile_skill.py --mode profile <target-skill-dir>

Prints one error per line and exits 1 when invalid; prints an OK line and
exits 0 when valid. The validator uses only the Python standard library and
enforces project-specific invariants; it does not claim to replace a full
Draft 2020-12 JSON Schema validator.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

MODES = ("plain", "profile")

SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$")
RESERVED_DOMAINS = ("algorithm", "interview", "resume-knowledge", "system", "profile")

RUNTIME_OPERATIONS = {
    "tool": "submit_event",
    "capabilitiesEvent": "system.capabilities.read",
    "identityResolveEvent": "system.user.resolve",
    "identityRegisterEvent": "system.user-registered",
    "profileReadEvent": "profile.snapshot.read",
    "evidenceWriteEvent": "profile.evidence.recorded",
    "directDriveAccess": False,
}
PLATFORMS = ["codex", "chatgpt", "claude", "workbuddy"]
ALLOWED_OUTCOMES = [
    "observed", "consulted", "stuck", "incorrect", "partial",
    "completed", "correct", "passed", "failed",
]
EVIDENCE_POLICY_FIELDS = (
    "recordWhen", "doNotRecordWhen", "allowedOutcomes",
    "sourceRefPolicy", "minimumEvidenceTextLength",
)

PROFILE_ONLY_PATHS = (
    "references/profile-contract.md",
    "schemas/profile-capability.json",
    "tests/test_profile_contract.py",
)
PROFILE_EVENT_TYPES = (
    "system.capabilities.read",
    "system.user.resolve",
    "system.user-registered",
    "profile.snapshot.read",
    "profile.evidence.recorded",
)

SCAFFOLD_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (r"TODO", r"TBD", r"FIXME", r"\[insert")
]
HOME_PATH_PATTERNS = [
    re.compile(r"[A-Za-z]:[\\/]"),
    re.compile(r"/Users/"),
    re.compile(r"/home/"),
    re.compile(r"/root/"),
]
DRIVE_PATTERNS = [
    re.compile(r"drive\.google\.com"),
    re.compile(r"docs\.google\.com"),
    re.compile(r'"fileId"\s*:'),
    re.compile(r"drive\.files\.create"),
    re.compile(r"\bcreateJson\b"),
    re.compile(r"googleapis\.com"),
]

MAX_FILE_BYTES = 2 * 1024 * 1024


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return f"\0unreadable:{error}"


def _parse_frontmatter(text: str, errors: list[str], rel: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        errors.append(f"{rel}: missing YAML frontmatter")
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        errors.append(f"{rel}: unterminated frontmatter")
        return {}
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        if not separator:
            errors.append(f"{rel}: malformed frontmatter line: {line.strip()}")
            continue
        fields[key.strip()] = value.strip()
    return fields


def _is_under(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _scan_text(text: str, rel: str, errors: list[str]) -> None:
    for pattern in SCAFFOLD_PATTERNS:
        match = pattern.search(text)
        if match:
            errors.append(f"{rel}: unfinished scaffold token {match.group(0)!r}")
            break
    for pattern in HOME_PATH_PATTERNS:
        match = pattern.search(text)
        if match:
            errors.append(f"{rel}: hardcoded home path pattern {match.group(0)!r} is not portable")
            break
    for pattern in DRIVE_PATTERNS:
        match = pattern.search(text)
        if match:
            errors.append(f"{rel}: direct Drive access marker {match.group(0)!r} is forbidden")
            break


def _validate_capability(document: object, skill_name: str, rel: str, errors: list[str]) -> None:
    if not isinstance(document, dict):
        errors.append(f"{rel}: capability document must be a JSON object")
        return
    expected_top = [
        "schemaVersion", "domain", "sourceSkill", "dimensions",
        "evidencePolicy", "runtime", "portability",
    ]
    for key in expected_top:
        if key not in document:
            errors.append(f"{rel}: missing required field {key!r}")
    if document.get("schemaVersion") != "1.0":
        errors.append(f"{rel}: schemaVersion must be the constant \"1.0\"")
    domain = document.get("domain")
    if not isinstance(domain, str) or not SAFE_ID.match(domain):
        errors.append(f"{rel}: domain must match the safe-identifier pattern")
    elif domain in RESERVED_DOMAINS:
        errors.append(f"{rel}: domain {domain!r} is reserved for existing implementations")
    source_skill = document.get("sourceSkill")
    if source_skill != skill_name:
        errors.append(f"{rel}: sourceSkill must equal the Skill folder name {skill_name!r}")
    dimensions = document.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        errors.append(f"{rel}: dimensions must be a non-empty array")
    else:
        for dimension in dimensions:
            if not isinstance(dimension, dict):
                errors.append(f"{rel}: each dimension must be an object")
                continue
            if not isinstance(dimension.get("dimensionKey"), str) or not SAFE_ID.match(dimension.get("dimensionKey", "")):
                errors.append(f"{rel}: dimensionKey must match the safe-identifier pattern")
            for key in ("subjectKeyDescription", "description"):
                if not isinstance(dimension.get(key), str) or not dimension.get(key):
                    errors.append(f"{rel}: dimension field {key!r} must be a non-empty string")
    evidence = document.get("evidencePolicy")
    if not isinstance(evidence, dict):
        errors.append(f"{rel}: evidencePolicy must be an object")
    else:
        for key in EVIDENCE_POLICY_FIELDS:
            if key not in evidence:
                errors.append(f"{rel}: evidencePolicy is missing {key!r}")
        if evidence.get("allowedOutcomes") != ALLOWED_OUTCOMES:
            errors.append(f"{rel}: evidencePolicy.allowedOutcomes must be the exact protocol outcome list")
        length = evidence.get("minimumEvidenceTextLength")
        if not isinstance(length, int) or isinstance(length, bool) or length < 1:
            errors.append(f"{rel}: minimumEvidenceTextLength must be an integer >= 1")
        for key in ("recordWhen", "doNotRecordWhen"):
            value = evidence.get(key)
            if not isinstance(value, list) or not value:
                errors.append(f"{rel}: evidencePolicy.{key} must be a non-empty array")
    runtime = document.get("runtime")
    if not isinstance(runtime, dict):
        errors.append(f"{rel}: runtime must be an object")
    else:
        for key, constant in RUNTIME_OPERATIONS.items():
            if runtime.get(key) != constant:
                errors.append(
                    f"{rel}: runtime.{key} must be the constant {constant!r}"
                )
    portability = document.get("portability")
    if not isinstance(portability, dict):
        errors.append(f"{rel}: portability must be an object")
    else:
        if portability.get("platforms") != PLATFORMS:
            errors.append(f"{rel}: portability.platforms must be the constant platform list")
        if portability.get("coreContractDependsOnOpenaiYaml") is not False:
            errors.append(f"{rel}: portability.coreContractDependsOnOpenaiYaml must be false")


def validate_skill(skill_dir: Path, mode: str) -> list[str]:
    """Return stable, sorted error messages; an empty list means valid."""
    if mode not in MODES:
        return [f"unknown mode {mode!r}; expected one of {MODES}"]
    errors: list[str] = []
    root = Path(skill_dir)
    try:
        root = root.resolve(strict=True)
    except OSError:
        return [f"target directory not found: {skill_dir}"]
    if not root.is_dir():
        return [f"target is not a directory: {skill_dir}"]

    # Walk the tree; every visited path must resolve inside the target root.
    # This rejects symlinks and Windows junctions/reparse points that escape
    # the explicitly supplied directory instead of traversing them.
    visited: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(dirpath)
        for name in sorted(dirnames):
            candidate = current / name
            if not _is_under(candidate.resolve(), root):
                errors.append(
                    f"{candidate.relative_to(root).as_posix()}: path resolves outside the target directory and is rejected"
                )
                dirnames.remove(name)
        for name in sorted(filenames):
            candidate = current / name
            resolved = candidate.resolve()
            if not _is_under(resolved, root):
                errors.append(
                    f"{candidate.relative_to(root).as_posix()}: path resolves outside the target directory"
                )
                continue
            if resolved.stat().st_size > MAX_FILE_BYTES:
                errors.append(f"{candidate.relative_to(root).as_posix()}: file exceeds size limit")
                continue
            visited.append(candidate)

    for path in visited:
        rel = path.relative_to(root).as_posix()
        text = _read_text(path)
        _scan_text(text, rel, errors)
        if path.suffix == ".json":
            try:
                json.loads(text)
            except json.JSONDecodeError as error:
                errors.append(f"{rel}: invalid JSON ({error.msg})")
        if mode == "plain":
            for event_type in PROFILE_EVENT_TYPES:
                if event_type in text:
                    errors.append(
                        f"{rel}: profile event type {event_type} is not allowed in plain mode"
                    )
                    break

    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        errors.append("SKILL.md: required entrypoint file is missing")
        return sorted(set(errors))

    skill_text = _read_text(skill_md)
    frontmatter = _parse_frontmatter(skill_text, errors, "SKILL.md")
    name = frontmatter.get("name")
    if name != root.name:
        errors.append(f"SKILL.md: frontmatter name must equal the folder name {root.name!r}")
    description = frontmatter.get("description", "")
    if not description.startswith("Use when"):
        errors.append("SKILL.md: description must begin with \"Use when\"")

    if mode == "plain":
        for rel in PROFILE_ONLY_PATHS:
            if (root / rel).exists():
                errors.append(f"{rel}: profile-only artifact is forbidden in plain mode")
        return sorted(set(errors))

    for rel in PROFILE_ONLY_PATHS:
        if not (root / rel).is_file():
            errors.append(f"{rel}: required profile artifact is missing")

    if "references/profile-contract.md" not in skill_text:
        errors.append("SKILL.md: must link references/profile-contract.md")

    capability_path = root / "schemas" / "profile-capability.json"
    if capability_path.is_file():
        try:
            document = json.loads(_read_text(capability_path))
        except json.JSONDecodeError as error:
            errors.append(f"schemas/profile-capability.json: invalid JSON ({error.msg})")
            document = None
        if document is not None:
            _validate_capability(
                document, name or root.name, "schemas/profile-capability.json", errors
            )

    return sorted(set(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a generated profile-aware Skill directory."
    )
    parser.add_argument("--mode", choices=MODES, required=True,
                        help="validation mode: plain or profile")
    parser.add_argument("skill_dir", type=Path,
                        help="the resolved target Skill directory")
    args = parser.parse_args(argv)
    errors = validate_skill(args.skill_dir, args.mode)
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"OK: {args.skill_dir} passes {args.mode} validation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
