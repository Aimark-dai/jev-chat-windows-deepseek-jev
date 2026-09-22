import json
import os
import unittest
from unittest.mock import patch

from core import typesafe_client


class _Response:
    def __init__(self, data):
        self._raw = json.dumps(data, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self._raw


class TypeSafeClientTests(unittest.TestCase):
    def test_ask_calls_official_systemone_api(self):
        api_response = {
            "model": "jev-1.13",
            "answers": {
                "best_reply": {
                    "type": "choice",
                    "choice": "reply_b",
                    "confidence": 0.9,
                    "probabilities": {"reply_a": 0.05, "reply_b": 0.9, "reply_c": 0.05},
                }
            },
            "usage": {"input_tokens": 20, "output_tokens": 4},
        }
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["auth"] = request.headers["Authorization"]
            captured["timeout"] = timeout
            return _Response(api_response)

        questions = {
            "best_reply": {
                "type": "choice",
                "criteria": {"reply_a": "A", "reply_b": "B", "reply_c": "C"},
            }
        }
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "typesafe-test-key"}, clear=False):
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                result = typesafe_client.ask({"messages": []}, questions, timeout=7)

        self.assertEqual(captured["url"], "https://api.typesafe.ai/v1/systemone")
        self.assertEqual(captured["body"]["model"], "jev-latest")
        self.assertEqual(captured["body"]["state"], {"messages": []})
        self.assertEqual(captured["auth"], "Bearer typesafe-test-key")
        self.assertEqual(captured["timeout"], 7)
        self.assertEqual(result["answers"]["best_reply"]["choice"], "reply_b")
        self.assertEqual(result["answers"]["best_reply"]["confidence"], 0.9)

    def test_ask_rejects_choice_outside_question_criteria(self):
        questions = {
            "candidate_quality": {
                "type": "choice",
                "criteria": {"pass": "usable", "regenerate": "rewrite"},
            }
        }
        response = {"answers": {"candidate_quality": {"choice": "send_anyway"}}}
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "typesafe-test-key"}, clear=False):
            with patch("urllib.request.urlopen", return_value=_Response(response)):
                with self.assertRaisesRegex(typesafe_client.JevError, "不在允许值"):
                    typesafe_client.ask({"messages": []}, questions)

    def test_ask_rejects_missing_required_answer(self):
        questions = {
            "candidate_quality": {
                "type": "choice",
                "criteria": {"pass": "usable", "regenerate": "rewrite"},
            }
        }
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "typesafe-test-key"}, clear=False):
            with patch("urllib.request.urlopen", return_value=_Response({"answers": {}})):
                with self.assertRaisesRegex(typesafe_client.JevError, "缺少 candidate_quality"):
                    typesafe_client.ask({"messages": []}, questions)

    def test_ask_accepts_typesafe_noul_probability(self):
        questions = {
            "literal_question": {
                "type": "noul",
                "criteria": {"true": "literal", "false": "subtext"},
            }
        }
        response = {"answers": {"literal_question": {"type": "noul", "noul": 0.65}}}
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "typesafe-test-key"}, clear=False):
            with patch("urllib.request.urlopen", return_value=_Response(response)):
                result = typesafe_client.ask({"messages": []}, questions)

        self.assertEqual(result["answers"]["literal_question"]["noul"], 0.65)

    def test_ask_rejects_invalid_choice_confidence(self):
        questions = {
            "true_intent": {
                "type": "choice",
                "criteria": {"casual_chat": "chat", "request_action": "action"},
            }
        }
        response = {
            "answers": {
                "true_intent": {
                    "type": "choice", "choice": "casual_chat", "confidence": 1.2,
                }
            }
        }
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "typesafe-test-key"}, clear=False):
            with patch("urllib.request.urlopen", return_value=_Response(response)):
                with self.assertRaisesRegex(typesafe_client.JevError, "confidence 超出 0-1"):
                    typesafe_client.ask({"messages": []}, questions)


if __name__ == "__main__":
    unittest.main()
