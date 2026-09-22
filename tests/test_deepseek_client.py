import json
import os
import unittest
from unittest.mock import patch

from core import jev_client


QUESTIONS = {
    "intent": {
        "type": "choice",
        "criteria": {"chat": "casual", "request": "wants action"},
    },
    "risk": {
        "type": "score",
        "criteria": ["none", "some", "high"],
    },
    "reply": {
        "type": "noul",
        "criteria": {"true": "reply", "false": "do not reply"},
    },
}


class _Response:
    def __init__(self, data):
        self._raw = json.dumps(data, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self._raw


class DeepSeekClientTests(unittest.TestCase):
    def test_validate_answers_accepts_choices_and_score(self):
        result = jev_client._validate_answers(
            {
                "answers": {
                    "intent": {"choice": "request"},
                    "risk": {"score": 2},
                    "reply": {"choice": True},
                }
            },
            QUESTIONS,
        )
        self.assertEqual(result["intent"]["choice"], "request")
        self.assertEqual(result["risk"]["score"], 2.0)
        self.assertEqual(result["reply"]["choice"], "true")

    def test_validate_answers_rejects_unknown_choice(self):
        with self.assertRaisesRegex(jev_client.JevError, "不在允许值"):
            jev_client._validate_answers(
                {
                    "answers": {
                        "intent": {"choice": "invented"},
                        "risk": {"score": 1},
                        "reply": {"choice": "false"},
                    }
                },
                QUESTIONS,
            )

    def test_ask_uses_deepseek_json_output_and_keeps_usage(self):
        answer = {
            "answers": {
                "intent": {"choice": "chat"},
                "risk": {"score": 0},
                "reply": {"choice": "true"},
            }
        }
        api_response = {
            "choices": [{"message": {"content": json.dumps(answer)}}],
            "usage": {"total_tokens": 123},
        }
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["auth"] = request.headers["Authorization"]
            captured["timeout"] = timeout
            return _Response(api_response)

        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "secret-test-key"}, clear=False):
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                result = jev_client.ask({"chat": {"messages": []}}, QUESTIONS, timeout=7)

        self.assertEqual(captured["url"], jev_client.API_URL)
        self.assertEqual(captured["body"]["model"], "deepseek-flash")
        self.assertEqual(captured["body"]["response_format"], {"type": "json_object"})
        self.assertEqual(captured["body"]["thinking"], {"type": "disabled"})
        self.assertEqual(captured["auth"], "Bearer secret-test-key")
        self.assertEqual(captured["timeout"], 7)
        self.assertEqual(result["answers"]["intent"]["choice"], "chat")
        self.assertEqual(result["usage"]["total_tokens"], 123)


if __name__ == "__main__":
    unittest.main()
