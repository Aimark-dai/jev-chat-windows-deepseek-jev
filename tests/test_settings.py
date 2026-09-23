import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import settings


class DeepSeekSettingsTests(unittest.TestCase):
    def test_save_uses_one_deepseek_key_and_forces_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            saved_keys = []
            with patch.object(settings, "_CONFIG", str(config)):
                with patch.object(settings, "_set_key", side_effect=lambda name, value: saved_keys.append((name, value))):
                    settings.save("ds-test", "friends", 8, provider_text="openrouter",
                                  auto_send_on=True)

            self.assertEqual(saved_keys, [("DEEPSEEK_API_KEY", "ds-test")])
            data = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(data["draft_provider"], "deepseek")
            self.assertEqual(data["relationship"], "friends")
            self.assertEqual(data["context"], 8)
            self.assertEqual(data["auto_send"], sys.platform != "darwin")

    def test_auto_send_defaults_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "missing.json"
            with patch.object(settings, "_CONFIG", str(config)):
                self.assertFalse(settings.auto_send())

    def test_save_typesafe_judge_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            saved_keys = []
            with patch.object(settings, "_CONFIG", str(config)):
                with patch.object(settings, "_set_key", side_effect=lambda name, value: saved_keys.append((name, value))):
                    settings.save(
                        "ds-test", "friends", typesafe_key_text="ts-test",
                        judge_provider_text="typesafe",
                    )

            self.assertEqual(
                saved_keys,
                [("DEEPSEEK_API_KEY", "ds-test"), ("TYPESAFE_API_KEY", "ts-test")],
            )
            data = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(data["judge_provider"], "typesafe")

    def test_auto_send_rejects_non_boolean_truthy_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text('{"auto_send": "false"}', encoding="utf-8")
            with patch.object(settings, "_CONFIG", str(config)):
                self.assertFalse(settings.auto_send())

    @unittest.skipIf(sys.platform == "darwin", "Mac 预览版禁止开启自动发送")
    def test_quick_auto_send_toggle_preserves_other_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text(
                json.dumps({"relationship": "friends", "context": 9, "style": "话少",
                            "reply_target": True, "thinking": False, "check_update": False}),
                encoding="utf-8",
            )
            with patch.object(settings, "_CONFIG", str(config)):
                settings.set_auto_send(True)

            data = json.loads(config.read_text(encoding="utf-8"))
            self.assertTrue(data["auto_send"])
            self.assertEqual(data["relationship"], "friends")
            self.assertEqual(data["context"], 9)
            self.assertEqual(data["style"], "话少")
            self.assertTrue(data["reply_target"])
            self.assertFalse(data["check_update"])


if __name__ == "__main__":
    unittest.main()
