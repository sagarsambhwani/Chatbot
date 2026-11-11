import sys
import os
import unittest
from unittest.mock import MagicMock
import asyncio

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from intelligence.analyzer import ConversationAnalyzer
from intelligence.schemas import ConversationAnalysis


class TestConversationAnalyzer(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.analyzer = ConversationAnalyzer(
            model="qwen2.5:1.5b",
            llm_client=self.mock_client
        )

    def test_structured_output_parsing_success(self):
        """Test valid JSON string is parsed into ConversationAnalysis."""
        valid_json = """{
            "intent": "coding",
            "topic": "QuickSort in Python",
            "knowledge_level": "intermediate",
            "desired_depth": "normal",
            "needs_example": true,
            "needs_analogy": false,
            "needs_code": true,
            "needs_web_search": false,
            "needs_rag": false,
            "needs_clarification": false,
            "clarification_question": null
        }"""
        self.mock_client.chat_structured.return_value = valid_json

        analysis = self.analyzer.analyze_sync("Write a quicksort function in python")

        self.assertEqual(analysis.intent, "coding")
        self.assertEqual(analysis.topic, "QuickSort in Python")
        self.assertTrue(analysis.needs_code)
        self.assertTrue(analysis.needs_example)
        self.assertFalse(analysis.needs_web_search)

    def test_invalid_json_fallback(self):
        """Test malformed JSON triggers safe fallback."""
        self.mock_client.chat_structured.return_value = "Not a JSON { broken: "

        analysis = self.analyzer.analyze_sync("What is python?")

        self.assertIsInstance(analysis, ConversationAnalysis)
        self.assertEqual(analysis.knowledge_level, "unknown")
        self.assertFalse(analysis.needs_clarification)

    def test_missing_fields_defaults(self):
        """Test partial JSON where defaults fill missing fields."""
        partial_json = """{
            "intent": "factual",
            "topic": "Python"
        }"""
        self.mock_client.chat_structured.return_value = partial_json

        analysis = self.analyzer.analyze_sync("Tell me about Python")

        self.assertEqual(analysis.intent, "factual")
        self.assertEqual(analysis.topic, "Python")
        self.assertEqual(analysis.knowledge_level, "unknown")
        self.assertEqual(analysis.desired_depth, "normal")

    def test_model_timeout_fallback(self):
        """Test network timeout triggers fallback safely without raising."""
        self.mock_client.chat_structured.side_effect = TimeoutError("Connection timed out")

        analysis = self.analyzer.analyze_sync("Latest price of Bitcoin?")

        self.assertIsInstance(analysis, ConversationAnalysis)
        # Fallback heuristic detects 'latest' and 'price'
        self.assertTrue(analysis.needs_web_search)

    def test_empty_user_message(self):
        """Test empty or whitespace-only messages."""
        analysis = self.analyzer.analyze_sync("   ")

        self.assertIsInstance(analysis, ConversationAnalysis)
        self.mock_client.chat_structured.assert_not_called()

    def test_empty_history(self):
        """Test message analysis with empty history."""
        self.mock_client.chat_structured.return_value = """{
            "intent": "casual",
            "topic": "greeting",
            "knowledge_level": "unknown",
            "desired_depth": "brief",
            "needs_example": false,
            "needs_analogy": false,
            "needs_code": false,
            "needs_web_search": false,
            "needs_rag": false,
            "needs_clarification": false,
            "clarification_question": null
        }"""
        analysis = self.analyzer.analyze_sync("Hello there", history=[])
        self.assertEqual(analysis.intent, "casual")

    def test_long_conversation_history_bounding(self):
        """Test history longer than 6 messages is truncated to 6 messages."""
        self.mock_client.chat_structured.return_value = """{
            "intent": "factual",
            "topic": "context test",
            "knowledge_level": "unknown",
            "desired_depth": "normal",
            "needs_example": false,
            "needs_analogy": false,
            "needs_code": false,
            "needs_web_search": false,
            "needs_rag": false,
            "needs_clarification": false,
            "clarification_question": null
        }"""
        long_history = [
            {"role": "user", "content": f"msg {i}"}
            for i in range(20)
        ]

        self.analyzer.analyze_sync("What did we talk about?", history=long_history)

        # Inspect call arguments
        call_args = self.mock_client.chat_structured.call_args
        messages_sent = call_args.kwargs.get("messages") or call_args[1].get("messages")
        # System prompt (1) + 6 bounded history items + user query (1) = 8
        self.assertEqual(len(messages_sent), 8)

    def test_async_analyze_method(self):
        """Test async analyze() method runs without error."""
        self.mock_client.chat_structured.return_value = """{
            "intent": "research",
            "topic": "Quantum decoherence",
            "knowledge_level": "advanced",
            "desired_depth": "deep",
            "needs_example": false,
            "needs_analogy": false,
            "needs_code": false,
            "needs_web_search": false,
            "needs_rag": false,
            "needs_clarification": false,
            "clarification_question": null
        }"""
        analysis = asyncio.run(self.analyzer.analyze("Explain quantum decoherence"))
        self.assertEqual(analysis.intent, "research")
        self.assertEqual(analysis.desired_depth, "deep")


if __name__ == "__main__":
    unittest.main()
