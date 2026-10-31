import unittest
from unittest.mock import AsyncMock, patch

from agent.graph import (
    _check_guardrails_input_async,
    _check_guardrails_output_async,
    _regex_fallback,
)


class SecretGuardrailTests(unittest.IsolatedAsyncioTestCase):
    guardrail = {
        "id": "gr-secret-detection",
        "name": "Credential & Secret Detection",
        "enabled": True,
        "severity": "critical",
        "category": "content_safety",
        "config": {"action": "block"},
    }

    def test_blocks_common_credential_material(self):
        result = _regex_fallback(
            "gr-secret-detection",
            "Authorization: Bearer sk-proj-" + "A" * 28,
            self.guardrail,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("OpenAI-style key", result["detail"])

    def test_allows_text_without_credential_material(self):
        result = _regex_fallback(
            "gr-secret-detection",
            "Please store the API key securely and rotate it regularly.",
            self.guardrail,
        )

        self.assertEqual(result["status"], "passed")

    async def test_output_guardrail_is_deterministic_even_if_llm_disagrees(self):
        token = "ghp_" + "A" * 36
        with patch("agent.memory.list_guardrails", return_value=[self.guardrail]), patch(
            "agent.graph._llm_guardrail_check",
            new=AsyncMock(return_value={self.guardrail["id"]: {"triggered": False}}),
        ):
            results = await _check_guardrails_output_async("token=" + token)

        self.assertEqual(results[0]["status"], "blocked")
        self.assertEqual(results[0]["id"], self.guardrail["id"])

    async def test_input_guardrail_blocks_common_secret_tokens(self):
        token = "ghp_" + "A" * 36
        with patch("agent.memory.list_guardrails", return_value=[self.guardrail]), patch(
            "agent.graph._llm_guardrail_check",
            new=AsyncMock(return_value={self.guardrail["id"]: {"triggered": False}}),
        ):
            results = await _check_guardrails_input_async("token=" + token)

        self.assertEqual(results[0]["status"], "blocked")
        self.assertEqual(results[0]["id"], self.guardrail["id"])


if __name__ == "__main__":
    unittest.main()