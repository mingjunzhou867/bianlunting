"""Route-level tests for saved-session retrieval endpoints."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from agents.debate_persistence import DebateSessionNotFoundError
from api.main import app


class RetrievalApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    @patch("api.main.list_saved_sessions")
    def test_history_endpoint_returns_summary_list(self, list_saved_sessions_mock) -> None:
        list_saved_sessions_mock.return_value = [
            {
                "session_id": "session-123",
                "id_card": "42090219760310000D",
                "status": "completed",
                "source_endpoint": "/api/debate",
                "final_conclusion": "符合",
                "final_stance": "支持通过",
                "consensus_rate": 1.0,
                "is_consensus_reached": True,
                "rounds_taken": 0,
                "evidence_count": 1,
                "completed_at": "2026-03-23T10:01:00",
            }
        ]

        response = self.client.get("/api/debates", params={"id_card": "42090219760310000D"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["data"]["id_card"], "42090219760310000D")
        self.assertEqual(payload["data"]["history"][0]["session_id"], "session-123")

    @patch("api.main.list_saved_sessions", return_value=[])
    def test_history_endpoint_returns_empty_list_when_no_sessions_exist(self, _list_saved_sessions_mock) -> None:
        response = self.client.get("/api/debates", params={"id_card": "42090219760310000D"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["data"]["history"], [])

    @patch("api.main.list_saved_sessions", return_value=[])
    def test_history_endpoint_allows_missing_id_card_query_param(self, list_saved_sessions_mock) -> None:
        response = self.client.get("/api/debates")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["data"]["id_card"], "")
        list_saved_sessions_mock.assert_called_once_with(id_card=None)

    @patch("api.main.get_saved_session_detail")
    def test_detail_endpoint_returns_snapshot_first_payload(self, get_saved_session_detail_mock) -> None:
        get_saved_session_detail_mock.return_value = {
            "session_id": "session-123",
            "id_card": "42090219760310000D",
            "status": "completed",
            "source_endpoint": "/api/debate",
            "completed_at": "2026-03-23T10:01:00",
            "final_conclusion": "符合",
            "evidence": [{"rule_id": "RULE_001"}],
            "history": [{"round_num": 0, "judgments": []}],
            "summary": {"final_conclusion": "符合"},
            "arbiter_result": {"summary": "维持多数意见"},
        }

        response = self.client.get("/api/debates/session-123")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["data"]["session_id"], "session-123")
        self.assertEqual(payload["data"]["summary"]["final_conclusion"], "符合")
        self.assertEqual(payload["data"]["arbiter_result"]["summary"], "维持多数意见")
        self.assertEqual(payload["data"]["source_endpoint"], "/api/debate")
        self.assertEqual(payload["data"]["evidence"][0]["rule_id"], "RULE_001")

    @patch(
        "api.main.get_saved_session_detail",
        side_effect=DebateSessionNotFoundError("Saved debate session not found: missing-session"),
    )
    def test_detail_endpoint_returns_404_for_missing_session(self, _get_saved_session_detail_mock) -> None:
        response = self.client.get("/api/debates/missing-session")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["detail"],
            "Saved debate session not found: missing-session",
        )

    def test_existing_debate_routes_remain_registered(self) -> None:
        routes = {(route.path, tuple(sorted(route.methods))) for route in app.routes if hasattr(route, "methods")}

        self.assertIn(("/api/debate", ("POST",)), routes)
        self.assertIn(("/api/debate_stream", ("POST",)), routes)


if __name__ == "__main__":
    unittest.main()
