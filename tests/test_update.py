# -*- coding: utf-8 -*-
import json
import unittest
from io import BytesIO
from unittest.mock import patch

from app import update


class _Response(BytesIO):
    def __init__(self, body=b"", url=""):
        super().__init__(body)
        self._url = url

    def geturl(self):
        return self._url


class UpdateTest(unittest.TestCase):
    def test_release_page_redirect_finds_newer_version(self):
        response = _Response(
            url="https://github.com/Aimark-dai/jev-chat-windows-deepseek-jev/releases/tag/v1.1.0"
        )
        with patch("urllib.request.urlopen", return_value=response) as open_url:
            self.assertEqual(
                update.check_latest("1.0.0"),
                (
                    "1.1.0",
                    "https://github.com/Aimark-dai/jev-chat-windows-deepseek-jev/releases/tag/v1.1.0",
                ),
            )
        self.assertEqual(open_url.call_count, 1)

    def test_api_is_fallback_when_release_page_fails(self):
        payload = json.dumps({
            "tag_name": "v1.2.0",
            "html_url": "https://github.com/Aimark-dai/jev-chat-windows-deepseek-jev/releases/tag/v1.2.0",
        }).encode()
        responses = [OSError("page unavailable"), _Response(payload)]
        with patch("urllib.request.urlopen", side_effect=responses) as open_url:
            self.assertEqual(
                update.check_latest("1.0.0"),
                (
                    "1.2.0",
                    "https://github.com/Aimark-dai/jev-chat-windows-deepseek-jev/releases/tag/v1.2.0",
                ),
            )
        self.assertEqual(open_url.call_count, 2)

    def test_current_version_does_not_report_update(self):
        response = _Response(
            url="https://github.com/Aimark-dai/jev-chat-windows-deepseek-jev/releases/tag/v1.0.0"
        )
        with patch("urllib.request.urlopen", return_value=response):
            self.assertIsNone(update.check_latest("1.0.0"))

    def test_development_version_does_not_make_request(self):
        with patch("urllib.request.urlopen") as open_url:
            self.assertIsNone(update.check_latest("0.0.0-dev"))
        open_url.assert_not_called()


if __name__ == "__main__":
    unittest.main()
