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
        pre_judged = {
            "answers": {
                "true_intent": {"type": "choice", "choice": "casual_chat"},
                "danger_level": {"type": "score", "score": 0},
                "best_action": {"type": "choice", "choice": "acknowledge"},
                "she_needs": {"type": "choice", "choice": "nothing"},
            },
            "usage": {"input_tokens": 40, "output_tokens": 4},
        }
        reviewed = {
            "answers": {
                "best_reply": {
                    "type": "choice",
                    "choice": "reply_c",
                    "probabilities": {"reply_a": 0.1, "reply_b": 0.2, "reply_c": 0.7},
                },
                "candidate_quality": {"type": "choice", "choice": "pass"},
                "rewrite_focus": {"type": "choice", "choice": "good"},
            },
            "usage": {"input_tokens": 80, "output_tokens": 5},
        }
        with patch.object(engine, "draft_candidates", return_value=["甲", "乙", "丙"]) as draft:
            with patch.object(engine, "typesafe_ask", side_effect=[pre_judged, reviewed]) as ask:
                result = engine.analyze(
                    [("her", "在吗")], "friends", judge_provider="typesafe"
                )

        self.assertEqual(ask.call_count, 2)
        self.assertEqual(draft.call_args.kwargs["jev_analysis"], pre_judged["answers"])
        self.assertEqual(result["best_reply"], "丙")
        self.assertEqual(result["scores"], [0.1, 0.2, 0.7])
        self.assertEqual(result["judge_provider"], "typesafe")
        self.assertTrue(result["quality_passed"])
        self.assertFalse(result["regenerated"])
        self.assertEqual(result["usage"]["typesafe_calls"], 2)

    def test_typesafe_rejection_regenerates_once_then_reviews_again(self):
        pre_judged = {
            "answers": {
                "true_intent": {"type": "choice", "choice": "request_action"},
                "best_action": {"type": "choice", "choice": "give_commitment"},
            },
            "usage": {},
        }
        rejected = {
            "answers": {
                "best_reply": {"type": "choice", "choice": "reply_a"},
                "candidate_quality": {"type": "choice", "choice": "regenerate"},
                "rewrite_focus": {"type": "choice", "choice": "wrong_intent"},
            },
            "usage": {},
        }
        accepted = {
            "answers": {
                "best_reply": {
                    "type": "choice",
                    "choice": "reply_b",
                    "probabilities": {"reply_a": 0.2, "reply_b": 0.7, "reply_c": 0.1},
                },
                "candidate_quality": {"type": "choice", "choice": "pass"},
                "rewrite_focus": {"type": "choice", "choice": "good"},
            },
            "usage": {},
        }
        with patch.object(
            engine,
            "draft_candidates",
            side_effect=[["旧甲", "旧乙", "旧丙"], ["新甲", "新乙", "新丙"]],
        ) as draft:
            with patch.object(
                engine, "typesafe_ask", side_effect=[pre_judged, rejected, accepted]
            ) as ask:
                result = engine.analyze(
                    [("her", "明天下午给我")], "colleagues", judge_provider="typesafe"
                )

        self.assertEqual(ask.call_count, 3)
        self.assertEqual(draft.call_count, 2)
        retry = draft.call_args_list[1].kwargs
        self.assertEqual(retry["jev_analysis"], pre_judged["answers"])
        self.assertEqual(retry["revision_feedback"], rejected["answers"])
        self.assertEqual(retry["rejected_candidates"], ["旧甲", "旧乙", "旧丙"])
        self.assertEqual(result["candidates"], ["新甲", "新乙", "新丙"])
        self.assertEqual(result["best_reply"], "新乙")
        self.assertTrue(result["quality_passed"])
        self.assertTrue(result["regenerated"])

    def test_typesafe_second_rejection_is_marked_for_manual_confirmation(self):
        pre_judged = {"answers": {}, "usage": {}}
        rejected = {
            "answers": {
                "best_reply": {"type": "choice", "choice": "reply_a"},
                "candidate_quality": {"type": "choice", "choice": "regenerate"},
                "rewrite_focus": {"type": "choice", "choice": "generic_or_robotic"},
            },
            "usage": {},
        }
        with patch.object(
            engine,
            "draft_candidates",
            side_effect=[["旧甲", "旧乙", "旧丙"], ["新甲", "新乙", "新丙"]],
        ):
            with patch.object(
                engine, "typesafe_ask", side_effect=[pre_judged, rejected, rejected]
            ):
                result = engine.analyze(
                    [("her", "在吗")], "friends", judge_provider="typesafe"
                )

        self.assertFalse(result["quality_passed"])
        self.assertTrue(result["regenerated"])


if __name__ == "__main__":
    unittest.main()
