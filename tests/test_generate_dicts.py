"""Tests for the dictionary generator skeleton."""
from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path

from scripts.generate_dicts import (
    build_default_candidates,
    build_manifest,
    normalize_candidate,
    parse_args,
    write_artifacts,
)


class TestGenerateDicts(unittest.TestCase):
    def _make_output_dir(self) -> Path:
        output_dir = Path.cwd() / ".test_tmp" / f"generate_dicts_{uuid.uuid4().hex}"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def test_default_candidates_include_adc310(self) -> None:
        names = {candidate.name for candidate in build_default_candidates()}
        self.assertIn("ADC310", names)
        self.assertIn("INSURER_STATUS", names)

    def test_normalize_candidate_produces_enhanced_shape(self) -> None:
        candidate = build_default_candidates()[0]
        artifact = normalize_candidate(candidate)
        payload = artifact.model_dump(mode="json")
        self.assertIn("name", payload)
        self.assertIn("description", payload)
        self.assertIn("values", payload)
        self.assertIn("source_refs", payload)
        self.assertIn("aliases", payload)
        self.assertIn("notes", payload)
        self.assertEqual(payload["total_count"], len(payload["values"]))

    def test_manifest_is_non_destructive(self) -> None:
        manifest = build_manifest(dict_ids=["ADC310"])
        self.assertEqual(len(manifest), 1)
        self.assertEqual(manifest[0]["name"], "ADC310")
        self.assertEqual(manifest[0]["output_file"], "ADC310.json")

    def test_write_artifacts_creates_json_files(self) -> None:
        output_dir = self._make_output_dir()
        try:
            written = write_artifacts(output_dir, dict_ids=["ADC310", "INSURER_STATUS"])
            self.assertEqual(
                {path.name for path in written},
                {"ADC310.json", "INSURER_STATUS.json"},
            )
            adc310 = json.loads((output_dir / "ADC310.json").read_text(encoding="utf-8"))
            self.assertIn("source_refs", adc310)
            self.assertIn("aliases", adc310)
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

    def test_parse_args_supports_dry_run_and_write(self) -> None:
        args = parse_args(["--write", "--dict-id", "ADC310"])
        self.assertTrue(args.write)
        self.assertEqual(args.dict_ids, ["ADC310"])


if __name__ == "__main__":
    unittest.main()
