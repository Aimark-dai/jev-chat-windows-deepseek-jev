import unittest
from unittest.mock import patch

from core import draft


class DeepSeekDraftTests(unittest.TestCase):
    def test_openrouter_provider_is_rejected(self):
        with self.assertRaisesRegex(draft.JevError, "只支持 DeepSeek"):
            draft.draft_candidates([("her", "在吗")], "friends", provider="openrouter")

    def test_jev_analysis_and_rewrite_feedback_are_sent_as_structured_context(self):
        with patch.object(draft, "_api_key", return_value="test-key"):
            with patch.object(draft, "_chat", return_value='["甲", "乙", "丙"]') as chat:
                result = draft.draft_candidates(
                    [("her", "明天下午给我")],
                    "colleagues",
                    jev_analysis={
                        "true_intent": {"choice": "request_action"},
                        "danger_level": {"score": 3},
                    },
                    revision_feedback={
                        "candidate_quality": {"choice": "regenerate"},
                        "rewrite_focus": {"choice": "factual_invention"},
                    },
                    rejected_candidates=["我保证马上完成", "放心吧", "肯定没问题"],
                )

        body = chat.call_args.args[2]
        prompt = body["messages"][1]["content"]
        self.assertEqual(result, ["甲", "乙", "丙"])
        self.assertEqual(body["temperature"], 0.6)
        self.assertIn('"true_intent": {"choice": "request_action"}', prompt)
        self.assertIn('"rewrite_focus": {"choice": "factual_invention"}', prompt)
        self.assertIn("我保证马上完成", prompt)


if __name__ == "__main__":
    unittest.main()
