"""Tests for semantic packet typed models and builder behavior."""
from __future__ import annotations

import shutil
import unittest
import uuid
from pathlib import Path

from cognition.semantic_packet import (
    DictExcerpt,
    SemanticPacket,
    SemanticPacketBuilder,
    StaticSemanticProvider,
    build_semantic_packet,
    load_dictionary_excerpt,
)
from scripts.generate_dicts import write_artifacts


class TestSemanticPacket(unittest.TestCase):
    def _make_output_dir(self) -> Path:
        output_dir = Path.cwd() / ".test_tmp" / f"semantic_packet_{uuid.uuid4().hex}"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def test_build_semantic_packet_returns_fixed_five_sections(self) -> None:
        packet = build_semantic_packet("42090219760310000D", "POLICY-FLEX")
        self.assertIsInstance(packet, SemanticPacket)
        self.assertTrue(packet.task)
        self.assertGreater(len(packet.fields), 0)
        self.assertGreater(len(packet.relations), 0)
        self.assertGreater(len(packet.time_semantics), 0)
        self.assertGreater(len(packet.dict_excerpt), 0)

    def test_task_entrypoint_preserves_policy_and_scope(self) -> None:
        packet = build_semantic_packet(
            "42090219760310000D",
            "POLICY-FLEX",
            qualification_scope="QI_BASIC_ACTIVE_PERSON",
        )
        self.assertEqual(packet.task.person_id, "42090219760310000D")
        self.assertEqual(packet.task.policy_id, "POLICY-FLEX")
        self.assertEqual(packet.task.qualification_scope, "QI_BASIC_ACTIVE_PERSON")

    def test_excerpt_first_default_behavior(self) -> None:
        packet = build_semantic_packet("42090219760310000D", "POLICY-FLEX")
        adc310 = next(excerpt for excerpt in packet.dict_excerpt if excerpt.dict_id == "ADC310")
        self.assertLess(len(adc310.relevant_values), 18)
        self.assertIn("050", adc310.relevant_values)

    def test_builder_uses_injected_provider(self) -> None:
        class CustomProvider(StaticSemanticProvider):
            def get_task_summary(self, person_id: str, policy_id: str, qualification_scope: str | None = None) -> str:
                return "custom-summary"

            def get_fields(self, person_id: str, policy_id: str, qualification_scope: str | None = None):
                return []

            def get_relations(self, person_id: str, policy_id: str, qualification_scope: str | None = None):
                return []

            def get_time_semantics(self, person_id: str, policy_id: str, qualification_scope: str | None = None):
                return []

            def get_dict_excerpts(self, person_id: str, policy_id: str, qualification_scope: str | None = None):
                return []

        packet = SemanticPacketBuilder(provider=CustomProvider()).build("p1", "policy-x")
        self.assertEqual(packet.task.summary, "custom-summary")
        self.assertEqual(packet.fields, [])

    def test_load_dictionary_excerpt_can_use_generated_seed_dir(self) -> None:
        output_dir = self._make_output_dir()
        try:
            write_artifacts(output_dir, dict_ids=["INSURER_STATUS"])
            excerpt = load_dictionary_excerpt(
                "INSURER_STATUS",
                field_name="social_insurance_payment.insurer_status",
                relevant_keys=["101"],
                dict_dir=output_dir,
            )
            self.assertIsInstance(excerpt, DictExcerpt)
            self.assertEqual(excerpt.relevant_values, {"101": "单位缴纳"})
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
