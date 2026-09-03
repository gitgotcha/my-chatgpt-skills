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
    "services/reliable-drive-sync-worker/src/legacy-reader.js",
    "services/reliable-drive-sync-worker/src/migration-store.js",
    "services/reliable-drive-sync-worker/test/legacy-reader.test.js",
    "services/reliable-drive-sync-worker/test/migration-store.test.js",
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
    ".worktrees",
    ".superpowers",
})

SKIP_RELATIVE_PREFIXES = ("docs/audits/", "upload/")

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
        relative = relative_path(path)
        if SKIP_DIRECTORIES.intersection(pathlib.PurePosixPath(relative).parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if relative.startswith(SKIP_RELATIVE_PREFIXES):
            continue
        if relative == relative_path(pathlib.Path(__file__).resolve()):
            continue
        yield path


class RepositoryStorageContractTest(unittest.TestCase):
    def test_repository_documents_are_scanned_from_worktree_checkout(self):
        files = list(documents())
        self.assertGreater(len(files), 20, "the scan silently covered nothing")
        names = {relative for relative in (relative_path(path) for path in files)}
        for expected in (
            "AGENTS.md",
            "services/reliable-drive-sync-worker/README.md",
            "services/reliable-drive-sync-worker/src/submit-event.js",
            "tools/reliable-drive-sync-mcp/stdio-bridge.mjs",
        ):
            self.assertIn(expected, names)

    def test_legacy_cloud_mcp_directory_is_removed(self):
        self.assertFalse((REPOSITORY_ROOT / "cloud-mcp").exists())

    def test_every_submit_event_skill_uses_outbox_receipt_semantics(self):
        skill_files = (
            "algorithm-learning/SKILL.md",
            "conducting-java-backend-mock-interviews/SKILL.md",
            "reviewing-java-backend-interviews/SKILL.md",
            "java-knowledge-based-on-resume-learn-skill/SKILL.md",
        )
        for relative in skill_files:
            text = (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(skill=relative):
                for required in ("deliveryState", "cloud_accepted", "pending", "SQLite", "D1 Outbox"):
                    self.assertIn(required, text)
                self.assertNotIn("receipt.fileId", text)

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
