import unittest
from unittest.mock import patch

from core import engine


class DeepSeekEngineTests(unittest.TestCase):
    def test_selected_style_reaches_draft_and_deepseek_judge(self):
        with patch.object(engine, "draft_candidates", return_value=["收到，我先核实后回复您。"]) as draft, \
             patch.object(engine, "deepseek_ask", return_value={"answers": {}}) as ask:
            engine.analyze([("her", "请问价格？")], "客户", style="专业商务：先核实再回复。")
        self.assertEqual(draft.call_args.kwargs["style"], "专业商务：先核实再回复。")
        self.assertEqual(ask.call_args.args[0]["chat"]["reply_style"], "专业商务：先核实再回复。")

    def test_selected_style_reaches_typesafe_pre_review_and_rewrite(self):
        reject = {"answers": {"candidate_quality": {"choice": "regenerate"}}}
        accept = {"answers": {"candidate_quality": {"choice": "pass"}}}
        with patch.object(engine, "draft_candidates", side_effect=[["初稿"], ["重写稿"]]) as draft, \
             patch.object(engine, "typesafe_ask", side_effect=[{"answers": {}}, reject, accept]) as ask:
            engine.analyze([("her", "请问价格？")], "客户", judge_provider="typesafe",
                           style="专业商务：先核实再回复。")
        self.assertEqual([call.kwargs["style"] for call in draft.call_args_list],
                         ["专业商务：先核实再回复。"] * 2)
        self.assertEqual([call.args[0]["chat"]["reply_style"] for call in ask.call_args_list],
                         ["专业商务：先核实再回复。"] * 3)
        self.assertIn("chat.reply_style", ask.call_args_list[1].args[1]["candidate_quality"]["instructions"])

    def test_jev_review_checks_unread_quote_is_not_confirmed_change(self):
        reject = {"answers": {"candidate_quality": {"choice": "regenerate"}}}
        accept = {"answers": {"candidate_quality": {"choice": "pass"}}}
        messages = [("her", "这个\n[引用：成员乙的消息，内容未完整识别]", "X")]
        with patch.object(engine, "draft_candidates", side_effect=[["这个改动我没注意过"], ["先核对原始说明"]]), \
             patch.object(engine, "typesafe_ask", side_effect=[{"answers": {}}, reject, accept]) as ask:
            engine.analyze(messages, "同行", judge_provider="typesafe")
        for call in ask.call_args_list:
            self.assertIn("引用：成员乙", call.args[0]["chat"]["messages"][0]["text"])
        review = ask.call_args_list[1].args[1]["candidate_quality"]["instructions"]
        rank = engine.build_rank_question(["甲", "乙"])["best_reply"]["instructions"]
        self.assertIn("unverified screenshot", review)
        self.assertIn("unverified screenshot", rank)
        self.assertIn("re-send", review)
        self.assertIn("re-send", rank)
        self.assertIn("quoted author", review)
        self.assertIn("unsupported personal memory", rank)

    def test_typesafe_pre_review_and_rewrite_share_ten_named_group_messages(self):
        messages = [("her", "不要传入的第零条", "旧人")]
        messages += [("her", f"第{i}条", "群友甲" if i % 2 else "群友乙") for i in range(1, 11)]
        reject = {"answers": {"candidate_quality": {"choice": "regenerate"}}}
        accept = {"answers": {"candidate_quality": {"choice": "pass"}}}
        with patch.object(engine, "draft_candidates", side_effect=[["甲", "乙"], ["丙", "丁"]]) as draft, \
             patch.object(engine, "typesafe_ask", side_effect=[{"answers": {}}, reject, accept]) as ask:
            engine.analyze(messages, "同行", context=10, reply_to="群友甲", judge_provider="typesafe")
        expected = [{"from": "her", "text": f"第{i}条", "name": "群友甲" if i % 2 else "群友乙"}
                    for i in range(1, 11)]
        for call in ask.call_args_list:
            self.assertEqual(call.args[0]["chat"]["messages"], expected)
            self.assertEqual(call.args[0]["chat"]["reply_to"], "群友甲")
        self.assertEqual([call.kwargs["keep"] for call in draft.call_args_list], [10, 10])
        self.assertTrue(all(call.args[0] == messages for call in draft.call_args_list))
        self.assertIn("group", ask.call_args_list[0].args[1]["true_intent"]["instructions"].lower())
        self.assertIn("first-person", ask.call_args_list[1].args[1]["candidate_quality"]["instructions"].lower())
        self.assertIn("first-person", ask.call_args_list[2].args[1]["best_reply"]["instructions"].lower())

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
        review_state = ask.call_args_list[1].args[0]
        self.assertEqual(
            review_state["candidate_replies"],
            [
                {"id": "reply_a", "text": "甲"},
                {"id": "reply_b", "text": "乙"},
                {"id": "reply_c", "text": "丙"},
            ],
        )
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
