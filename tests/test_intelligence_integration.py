import sys
import os
import unittest
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai_infra.llm_client import OllamaClient
from intelligence.semantic_router import SemanticRouter
from intelligence.response_planner import ResponsePlanner
from backend.assistant import LocalAssistant


class TestIntelligenceIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = OllamaClient()
        cls.is_ollama_available = cls.client.is_healthy()
        if not cls.is_ollama_available:
            print("\n[Notice] Local Ollama server is offline. Skipping live model integration tests.")

    def setUp(self):
        self.assistant = LocalAssistant(llm_client=self.client)

    def test_live_analyzer_structured_output(self):
        """Test analyzer against live Ollama model with structured JSON Schema."""
        if not self.is_ollama_available:
            self.skipTest("Ollama is not available.")

        t0 = time.time()
        analysis = self.assistant.analyzer.analyze_sync("Write a Python function to calculate fibonacci numbers")
        elapsed = round(time.time() - t0, 3)
        print(f"\n[Test] Live Analyzer latency: {elapsed}s | Intent: {analysis.intent} | Needs code: {analysis.needs_code}")

        self.assertIn(analysis.intent, ["coding", "technical_help"])
        self.assertTrue(analysis.needs_code)
        self.assertFalse(analysis.needs_web_search)

    def test_live_analyzer_web_search_detection(self):
        """Test analyzer correctly flags live external search for time-sensitive query."""
        if not self.is_ollama_available:
            self.skipTest("Ollama is not available.")

        analysis = self.assistant.analyzer.analyze_sync("What is the current stock price of Apple today?")
        print(f"\n[Test] Web search intent: {analysis.intent} | Needs web search: {analysis.needs_web_search}")
        self.assertTrue(analysis.needs_web_search)

    def test_live_planner_integration(self):
        """Test planner creates response plan from live analysis."""
        if not self.is_ollama_available:
            self.skipTest("Ollama is not available.")

        analysis = self.assistant.analyzer.analyze_sync("Explain what is an API for a beginner")
        plan = self.assistant.planner.create_plan(analysis)

        self.assertEqual(plan.response_type, "conceptual_explanation")
        self.assertIn(plan.explanation_style, ["progressive", "conversational"])

    def test_assistant_generate_response_e2e(self):
        """Test full assistant response generation including analysis, plan, and latencies."""
        if not self.is_ollama_available:
            self.skipTest("Ollama is not available.")

        res = self.assistant.generate_response(
            user_prompt="What is Python in one sentence?",
            use_web=False,
            use_rag=False
        )

        self.assertIn("answer", res)
        self.assertIn("latencies", res)
        self.assertIn("analyzer_seconds", res["latencies"])
        self.assertIn("llm_seconds", res["latencies"])
        self.assertIn("analysis", res)
        self.assertIn("plan", res)
        print(f"\n[Test] Full Assistant Turn Latencies: {res['latencies']}")


if __name__ == "__main__":
    unittest.main()
