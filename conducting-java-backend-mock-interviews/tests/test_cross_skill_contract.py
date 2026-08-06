from __future__ import annotations

import unittest
from pathlib import Path


class SharedSchemaTests(unittest.TestCase):
    def test_schema_copies_are_byte_identical(self) -> None:
        conducting_root = Path(__file__).resolve().parents[1]
        reviewing_root = conducting_root.parent / "reviewing-java-backend-interviews"
        conducting_schema = conducting_root / "schemas" / "contracts.schema.json"
        reviewing_schema = reviewing_root / "schemas" / "contracts.schema.json"

        self.assertEqual(conducting_schema.read_bytes(), reviewing_schema.read_bytes())

