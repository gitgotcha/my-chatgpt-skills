#!/usr/bin/env python3
"""Deterministic validator for generated profile-aware Skills.

Usage:

    python scripts/validate_profile_skill.py --mode plain <target-skill-dir>
    python scripts/validate_profile_skill.py --mode profile <target-skill-dir>

Prints one error per line and exits 1 when invalid; prints an OK line and
exits 0 when valid. The validator uses only the Python standard library: it
enforces project-specific invariants (target-path isolation, no home paths, no
Drive access, frontmatter allow-list) and, for profile Skills, executes the
shipped ``schemas/profile-capability.schema.json`` (Draft 2020-12 subset) so
generated capability documents are checked against the same contract the
schema declares.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

MODES = ("plain", "profile")

# Frontmatter fields permitted by the official Codex/OpenAI skill validator.
# The project validator rejects any field outside this set, mirroring the
# official allow-list so officially-illegal fields (e.g. ``interface``) fail.
OFFICIAL_FRONTMATTER_FIELDS = {"name", "description", "license", "allowed-tools", "metadata"}

# Generated profile contract tests must cover these four runtime behaviors.
# The validator requires each behavior to appear (by an unambiguous token) in
# the test source and requires the tests to actually execute and pass.
CONTRACT_MIN_TESTS = 4
CONTRACT_BEHAVIORS = (
    ("capabilities preflight and fail-closed", (
        "system.capabilities.read", "capabilities.read", "capabilities read",
        "fail-closed", "fail closed", "unsupported", "preflight",
    )),
    ("user consent before profile mutation", (
        "system.user.resolve", "user.resolve", "consent", "user-registered",
        "user_registered", "register", "explicit",
    )),
    ("immutable, read-only evidence", (
        "profile.evidence.recorded", "evidence.recorded", "profile.snapshot.read",
        "snapshot.read", "immutable", "append-only", "overwrite",
    )),
    ("full scan and preservation of existing files", (
        "full file scan", "full-file-scan", "byte-for-byte", "preserve",
        "preservation", "existing", "inventory", "scan",
    )),
)
# Default: execute generated contract tests as part of profile validation.
_EXECUTE_CONTRACT_TESTS = True

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

# The capability JSON Schema shipped with this meta Skill. The validator
# executes it directly, so generated capability documents are checked against
# the same contract the schema declares (additionalProperties, const, enum,
# pattern, minLength, maxLength, minItems, uniqueItems, required, items,
# properties, not) rather than only an ad-hoc re-implementation.
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "profile-capability.schema.json"


def _schema_type_matches(value: object, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    return True


def _schema_canonical(item: object) -> str:
    try:
        return json.dumps(item, sort_keys=True, default=str)
    except TypeError:
        return repr(item)


def _validate_against_schema(instance: object, schema: object, path: str, errors: list[str]) -> None:
    """Minimal Draft 2020-12 subset validator (standard library only)."""
    if not isinstance(schema, dict):
        return
    if "type" in schema and not _schema_type_matches(instance, schema["type"]):
        errors.append(f"{path}: expected type {schema['type']}")
        return
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: must equal the constant {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: must be one of {schema['enum']!r}")
    if "pattern" in schema and isinstance(instance, str):
        if re.search(schema["pattern"], instance) is None:
            errors.append(f"{path}: must match pattern {schema['pattern']!r}")
    if "minLength" in schema and isinstance(instance, str) and len(instance) < schema["minLength"]:
        errors.append(f"{path}: shorter than minLength {schema['minLength']}")
    if "maxLength" in schema and isinstance(instance, str) and len(instance) > schema["maxLength"]:
        errors.append(f"{path}: longer than maxLength {schema['maxLength']}")
    if "minItems" in schema and isinstance(instance, list) and len(instance) < schema["minItems"]:
        errors.append(f"{path}: fewer than minItems {schema['minItems']}")
    if "uniqueItems" in schema and schema["uniqueItems"] and isinstance(instance, list):
        seen = [_schema_canonical(item) for item in instance]
        if len(seen) != len(set(seen)):
            errors.append(f"{path}: items must be unique")
    if "not" in schema:
        sub_errors: list[str] = []
        _validate_against_schema(instance, schema["not"], path, sub_errors)
        if not sub_errors:
            errors.append(f"{path}: must not satisfy the negated constraint")
    if isinstance(instance, dict):
        for req in schema.get("required", []):
            if req not in instance:
                errors.append(f"{path}: missing required field {req!r}")
        props = schema.get("properties", {})
        for key, val in instance.items():
            if key in props:
                _validate_against_schema(val, props[key], f"{path}.{key}", errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unknown field {key!r}")
    if isinstance(instance, list) and "items" in schema:
        for index, item in enumerate(instance):
            _validate_against_schema(item, schema["items"], f"{path}[{index}]", errors)


_SCHEMA_CACHE: dict[str, object] = {}


def _load_capability_schema() -> object | None:
    if "document" in _SCHEMA_CACHE:
        return _SCHEMA_CACHE["document"]
    if not SCHEMA_PATH.is_file():
        return None
    try:
        document = json.loads(_read_text(SCHEMA_PATH))
    except (OSError, json.JSONDecodeError):
        return None
    _SCHEMA_CACHE["document"] = document
    return document


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


def _count_unittest_tests(output: str) -> int:
    """Extract the 'Ran N test(s)' count from unittest verbose output."""
    match = re.search(r"Ran (\d+) test", output)
    return int(match.group(1)) if match else 0


def _validate_contract_test(root: Path, errors: list[str]) -> None:
    """Enforce the four contract behaviors and actual execution of the
    generated profile contract tests.

    A placeholder test file (e.g. a single ``self.assertTrue(True)``) passes
    neither the behavior-coverage check nor the minimum test count, so it is
    rejected rather than mistaken for a real forward test.
    """
    test_path = root / "tests" / "test_profile_contract.py"
    if not test_path.is_file():
        return  # the missing-file error is recorded elsewhere
    text = _read_text(test_path).lower()
    for name, tokens in CONTRACT_BEHAVIORS:
        if not any(token in text for token in tokens):
            errors.append(
                f"tests/test_profile_contract.py: contract behavior not covered: {name}"
            )
    if not _EXECUTE_CONTRACT_TESTS:
        return
    command = [
        sys.executable, "-B", "-m", "unittest", "discover",
        "-s", str(root / "tests"), "-p", "test_*.py", "-v",
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as error:
        errors.append(
            f"tests/test_profile_contract.py: could not execute contract tests ({error})"
        )
        return
    if completed.returncode != 0:
        errors.append("tests/test_profile_contract.py: contract tests failed during execution")
        return
    # unittest writes its summary ("Ran N tests") to stderr, not stdout.
    collected = _count_unittest_tests(completed.stdout + "\n" + completed.stderr)
    if collected < CONTRACT_MIN_TESTS:
        errors.append(
            f"tests/test_profile_contract.py: only {collected} tests collected, "
            f"expected at least {CONTRACT_MIN_TESTS}"
        )


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

    # Validate top-level fields (only allowed ones)
    allowed_top_fields = {
        "schemaVersion", "domain", "sourceSkill", "dimensions",
        "evidencePolicy", "runtime", "portability",
    }
    for key in document:
        if key not in allowed_top_fields:
            errors.append(f"{rel}: unknown top-level field {key!r}; allowed fields: {sorted(allowed_top_fields)}")

    expected_top = ["schemaVersion", "domain", "sourceSkill", "dimensions",
                    "evidencePolicy", "runtime", "portability"]
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
            # Validate dimension fields
            allowed_dim_fields = {"dimensionKey", "subjectKeyDescription", "description"}
            for key in dimension:
                if key not in allowed_dim_fields:
                    errors.append(f"{rel}: dimension has unknown field {key!r}; allowed fields: {sorted(allowed_dim_fields)}")
            if not isinstance(dimension.get("dimensionKey"), str) or not SAFE_ID.match(dimension.get("dimensionKey", "")):
                errors.append(f"{rel}: dimensionKey must match the safe-identifier pattern")
            for key in ("subjectKeyDescription", "description"):
                if not isinstance(dimension.get(key), str) or not dimension.get(key):
                    errors.append(f"{rel}: dimension field {key!r} must be a non-empty string")
    dimension_keys = [d.get("dimensionKey") for d in dimensions if isinstance(d, dict)]
    if len(dimension_keys) != len(set(dimension_keys)):
        errors.append(f"{rel}: dimensionKey values must be unique")
    evidence = document.get("evidencePolicy")
    if not isinstance(evidence, dict):
        errors.append(f"{rel}: evidencePolicy must be an object")
    else:
        allowed_evidence_fields = {
            "recordWhen", "doNotRecordWhen", "allowedOutcomes",
            "sourceRefPolicy", "minimumEvidenceTextLength",
        }
        for key in evidence:
            if key not in allowed_evidence_fields:
                errors.append(f"{rel}: evidencePolicy has unknown field {key!r}; allowed fields: {sorted(allowed_evidence_fields)}")
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
        allowed_runtime_fields = set(RUNTIME_OPERATIONS.keys())
        for key in runtime:
            if key not in allowed_runtime_fields:
                errors.append(f"{rel}: runtime has unknown field {key!r}; allowed fields: {sorted(allowed_runtime_fields)}")
        for key, constant in RUNTIME_OPERATIONS.items():
            if runtime.get(key) != constant:
                errors.append(
                    f"{rel}: runtime.{key} must be the constant {constant!r}"
                )
    portability = document.get("portability")
    if not isinstance(portability, dict):
        errors.append(f"{rel}: portability must be an object")
    else:
        allowed_portability_fields = {"platforms", "coreContractDependsOnOpenaiYaml"}
        for key in portability:
            if key not in allowed_portability_fields:
                errors.append(f"{rel}: portability has unknown field {key!r}; allowed fields: {sorted(allowed_portability_fields)}")
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
        # Never descend into or scan Python bytecode caches; their embedded
        # source paths would otherwise trigger false home-path violations.
        if "__pycache__" in dirnames:
            dirnames.remove("__pycache__")
        current = Path(dirpath)
        for name in sorted(dirnames):
            candidate = current / name
            if not _is_under(candidate.resolve(), root):
                errors.append(
                    f"{candidate.relative_to(root).as_posix()}: path resolves outside the target directory and is rejected"
                )
                dirnames.remove(name)
        for name in sorted(filenames):
            if name.endswith(".pyc"):
                continue
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

    # Validate frontmatter against the official skill allow-list. The official
    # validator rejects any unknown field, so the project validator must too.
    for field in frontmatter:
        if field not in OFFICIAL_FRONTMATTER_FIELDS:
            errors.append(
                f"SKILL.md: unknown frontmatter field {field!r}; "
                f"only {sorted(OFFICIAL_FRONTMATTER_FIELDS)} are allowed"
            )

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

    _validate_contract_test(root, errors)

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
            # Full execution of the shipped capability JSON Schema: this is the
            # authoritative contract check (const, enum, pattern, minLength,
            # minItems, uniqueItems, additionalProperties, required, items).
            schema_document = _load_capability_schema()
            if schema_document is not None:
                _validate_against_schema(
                    document, schema_document, "schemas/profile-capability.json", errors
                )

    return sorted(set(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a generated profile-aware Skill directory."
    )
    parser.add_argument("--mode", choices=MODES, required=True,
                        help="validation mode: plain or profile")
    parser.add_argument("--no-execute-contract-tests", action="store_true",
                        help="skip executing generated contract tests (markers only)")
    parser.add_argument("skill_dir", type=Path,
                        help="the resolved target Skill directory")
    args = parser.parse_args(argv)
    global _EXECUTE_CONTRACT_TESTS
    _EXECUTE_CONTRACT_TESTS = not args.no_execute_contract_tests
    errors = validate_skill(args.skill_dir, args.mode)
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"OK: {args.skill_dir} passes {args.mode} validation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
