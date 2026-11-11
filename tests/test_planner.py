import sys
import os
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from intelligence.schemas import ConversationAnalysis
from intelligence.response_planner import ResponsePlanner


class TestResponsePlanner(unittest.TestCase):
    def setUp(self):
        self.planner = ResponsePlanner()

    def test_case_1_deep_conceptual_question(self):
        """Case 1: Deep conceptual question."""
        analysis = ConversationAnalysis(
            intent="conceptual_learning",
            topic="Transformers architecture",
            knowledge_level="intermediate",
            desired_depth="deep",
            needs_example=True,
            needs_analogy=True
        )
        plan = self.planner.create_plan(analysis)

        self.assertEqual(plan.response_type, "conceptual_explanation")
        self.assertEqual(plan.target_length, "long")
        self.assertEqual(plan.explanation_style, "progressive")
        self.assertTrue(plan.include_example)
        self.assertTrue(plan.include_analogy)
        self.assertTrue(plan.include_caveats)

    def test_case_2_brief_factual_question(self):
        """Case 2: Brief factual question."""
        analysis = ConversationAnalysis(
            intent="factual",
            topic="Capital of Japan",
            knowledge_level="beginner",
            desired_depth="brief",
            needs_example=False
        )
        plan = self.planner.create_plan(analysis)

        self.assertEqual(plan.response_type, "direct_answer")
        self.assertEqual(plan.target_length, "short")
        self.assertEqual(plan.explanation_style, "simple")
        self.assertFalse(plan.include_example)
        # Brief should have pruned redundant sections
        self.assertEqual(plan.sections, ["Direct answer"])

    def test_case_3_coding_question(self):
        """Case 3: Coding question."""
        analysis = ConversationAnalysis(
            intent="coding",
            topic="Reverse a linked list in Python",
            knowledge_level="intermediate",
            desired_depth="normal",
            needs_code=True
        )
        plan = self.planner.create_plan(analysis)

        self.assertEqual(plan.response_type, "technical_solution")
        self.assertEqual(plan.explanation_style, "technical")
        self.assertTrue(plan.include_code)
        self.assertIn("Implementation", plan.sections)

    def test_case_4_troubleshooting(self):
        """Case 4: Troubleshooting."""
        analysis = ConversationAnalysis(
            intent="troubleshooting",
            topic="Flask 500 error debugging",
            knowledge_level="intermediate",
            desired_depth="normal"
        )
        plan = self.planner.create_plan(analysis)

        self.assertEqual(plan.response_type, "troubleshooting")
        self.assertEqual(plan.explanation_style, "progressive")
        self.assertIn("Verification", plan.sections)
        self.assertTrue(plan.include_caveats)

    def test_case_5_research(self):
        """Case 5: Research."""
        analysis = ConversationAnalysis(
            intent="research",
            topic="Efficient LLM inference techniques",
            knowledge_level="advanced",
            desired_depth="deep"
        )
        plan = self.planner.create_plan(analysis)

        self.assertEqual(plan.response_type, "step_by_step")
        self.assertEqual(plan.explanation_style, "technical")
        self.assertEqual(plan.target_length, "long")
        self.assertIn("Conclusions", plan.sections)

    def test_case_6_casual_follow_up(self):
        """Case 6: Casual follow-up."""
        analysis = ConversationAnalysis(
            intent="casual",
            topic="Simplification follow-up",
            knowledge_level="beginner",
            desired_depth="normal"
        )
        plan = self.planner.create_plan(analysis)

        self.assertEqual(plan.response_type, "direct_answer")
        self.assertEqual(plan.explanation_style, "conversational")


if __name__ == "__main__":
    unittest.main()
