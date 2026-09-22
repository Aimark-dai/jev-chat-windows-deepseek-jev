import unittest
from unittest.mock import patch

from core import engine


class DeepSeekEngineTests(unittest.TestCase):
    def test_deepseek_is_the_default_provider(self):
        judged = {"answers": {}, "usage": {}}
        with patch.object(engine, "draft_candidates", return_value=["甲"]) as draft:
            with patch.object(engine, "deepseek_ask", return_value=judged):
                result = engine.analyze([("her", "在吗")], "friends")

        self.assertEqual(draft.call_args.kwargs["provider"], "deepseek")
        self.assertEqual(result["best_reply"], "甲")

    def test_selected_reply_works_without_probabilities(self):
        judged = {
            "answers": {
                "best_reply": {"type": "choice", "choice": "reply_b"},
                "true_intent": {"type": "choice", "choice": "casual_chat"},
                "danger_level": {"type": "score", "score": 0},
                "best_action": {"type": "choice", "choice": "acknowledge"},
                "she_needs": {"type": "choice", "choice": "nothing"},
            },
            "usage": {"total_tokens": 50},
        }
        with patch.object(engine, "draft_candidates", return_value=["甲", "乙", "丙"]):
            with patch.object(engine, "deepseek_ask", return_value=judged):
                result = engine.analyze([("her", "在吗")], "friends", provider="deepseek")

        self.assertEqual(result["best_index"], 1)
        self.assertEqual(result["best_reply"], "乙")
        self.assertEqual(result["scores"], [0.0, 0.0, 0.0])
        self.assertEqual(result["usage"]["total_tokens"], 50)

    def test_typesafe_judge_returns_calibrated_reply_probabilities(self):
        judged = {
            "answers": {
                "best_reply": {
                    "type": "choice",
                    "choice": "reply_c",
                    "probabilities": {"reply_a": 0.1, "reply_b": 0.2, "reply_c": 0.7},
                }
            },
            "usage": {"input_tokens": 80, "output_tokens": 5},
        }
        with patch.object(engine, "draft_candidates", return_value=["甲", "乙", "丙"]):
            with patch.object(engine, "typesafe_ask", return_value=judged) as ask:
                result = engine.analyze(
                    [("her", "在吗")], "friends", judge_provider="typesafe"
                )

        ask.assert_called_once()
        self.assertEqual(result["best_reply"], "丙")
        self.assertEqual(result["scores"], [0.1, 0.2, 0.7])
        self.assertEqual(result["judge_provider"], "typesafe")


if __name__ == "__main__":
    unittest.main()
