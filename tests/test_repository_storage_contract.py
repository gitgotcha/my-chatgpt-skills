"""Repository-wide guard for the unified storage contract.

Every cloud write must go through the single `submit_event` tool and land below
the one canonical root `DriveRoot/my-chatGPT-skills/users/<userId>/<domain>/`.
Namespace-scoped directories, the old profile layout and the removed candidate
identity tools are retired: they may only appear in the compatibility reader,
the migration implementation, their tests, historical planning documents, or
historical references that carry an explicit archived banner.
"""

import pathlib
import unittest

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Retired literals. Anything still matching these describes the pre-normalization
# world, which no active file is allowed to instruct a caller to use.
RETIRED_TOKENS = (
    "algorithm/users/",
    "interview/users/",
    "profile/current",
    "profile/history",
    "system/candidate_index.json",
    "candidates/<candidate_id>/",
    "identity.list",
    "identity.create",
    "identity.verify",
)

# The only places that may name the retired layout: the read-only compatibility
# reader, the non-destructive migration, and their own tests.
ALLOWED_PATHS = frozenset({
    "cloud-mcp/src/legacy-reader.js",
    "cloud-mcp/src/migration-store.js",
    "cloud-mcp/test/legacy-reader.test.js",
    "cloud-mcp/test/migration-store.test.js",
})

# Historical design and planning documents keep the old wording on purpose.
ALLOWED_PREFIXES = ("docs/superpowers/",)

# A historical reference is allowed as long as it says so up front.
ARCHIVED_BANNER = "archived / superseded"

SKIP_DIRECTORIES = frozenset({
    ".git",
    ".github",
    ".workbuddy-ai",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
})

SKIP_SUFFIXES = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".docx", ".xlsx", ".pptx", ".pdf", ".zip", ".gz", ".jar",
    ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3", ".exe", ".dll",
})


def relative_path(path):
    return path.relative_to(REPOSITORY_ROOT).as_posix()


def is_allowed(relative, text):
    if relative in ALLOWED_PATHS:
        return True
    if relative.startswith(ALLOWED_PREFIXES):
        return True
    return ARCHIVED_BANNER in text.lower()


def documents():
    """Every repository file that this contract can meaningfully inspect."""
    for path in sorted(REPOSITORY_ROOT.rglob("*")):
        if not path.is_file():
            continue
        if SKIP_DIRECTORIES.intersection(path.parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if relative_path(path) == relative_path(pathlib.Path(__file__).resolve()):
            continue
        yield path


class RepositoryStorageContractTest(unittest.TestCase):
    def test_repository_documents_are_scanned(self):
        files = list(documents())
        self.assertGreater(len(files), 20, "the scan silently covered nothing")
        names = {relative for relative in (relative_path(path) for path in files)}
        for expected in ("AGENTS.md", "cloud-mcp/README.md", "cloud-mcp/src/submit-event.js"):
            self.assertIn(expected, names)

    def test_no_active_file_uses_retired_storage_paths(self):
        offenders = []
        for path in documents():
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            relative = relative_path(path)
            if is_allowed(relative, text):
                continue
            hits = [token for token in RETIRED_TOKENS if token in text]
            if hits:
                offenders.append((relative, hits))
        self.assertEqual(offenders, [], "\n".join(f"{name}: {hits}" for name, hits in offenders))

    def test_allow_list_covers_only_compatibility_and_migration(self):
        for relative in sorted(ALLOWED_PATHS):
            path = REPOSITORY_ROOT / relative
            self.assertTrue(path.is_file(), f"allow-listed file is missing: {relative}")
            self.assertTrue(
                "legacy" in relative or "migration" in relative,
                f"allow-listed file is neither legacy nor migration code: {relative}"
            )


if __name__ == "__main__":
    unittest.main()
