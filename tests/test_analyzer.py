import sys
import os
import unittest
from unittest.mock import MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from intelligence.semantic_router import SemanticRouter
from intelligence.schemas import ConversationAnalysis


class TestSemanticRouter(unittest.TestCase):
    def setUp(self):
        # Mock client to avoid needing live Ollama for pure unit tests
        self.mock_client = MagicMock()
        # Return dummy 4-dim embedding
        self.mock_client.get_embedding.return_value = [0.1, 0.2, 0.3, 0.4]
        self.router = SemanticRouter(client=self.mock_client)

    def test_empty_message(self):
        analysis = self.router.analyze("")
        self.assertEqual(analysis.intent, "casual")
        self.assertFalse(analysis.needs_web_search)
        self.assertFalse(analysis.needs_rag)

    def test_explicit_search_directive(self):
        analysis = self.router.analyze("do web search on this: who won the match")
        self.assertTrue(analysis.needs_web_search)

if __name__ == "__main__":
    unittest.main()
