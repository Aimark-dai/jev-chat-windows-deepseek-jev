import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app import settings
from app.overlay import Overlay, _STYLES


class StylePresetTests(unittest.TestCase):
    def test_preset_and_legacy_custom_style_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text(json.dumps({"relationship": "friends", "style": "少用标点"}),
                              encoding="utf-8")
            with patch.object(settings, "_CONFIG", str(config)), \
                 patch.object(settings, "has_key", return_value=True), \
                 patch.object(settings, "has_typesafe_key", return_value=False):
                overlay = Overlay(on_fill=lambda _text: None)
                try:
                    self.assertEqual(overlay.styleBox.currentText(), "自定义")
                    self.assertEqual(overlay.styleEdit.text(), "少用标点")
                    self.assertTrue(overlay.styleEdit.isVisibleTo(overlay.settingsPage))

                    index = next(i for i, (name, _) in enumerate(_STYLES) if name == "专业商务")
                    overlay.styleBox.setCurrentIndex(index)
                    self.assertFalse(overlay.styleEdit.isVisibleTo(overlay.settingsPage))
                    overlay._save()
                    self.assertEqual(settings.style(), _STYLES[index][1])
                    self.assertEqual(overlay.styleBox.currentText(), "专业商务")

                    overlay.styleBox.setCurrentIndex(0)
                    overlay._save()
                    self.assertEqual(settings.style(), "")
                finally:
                    overlay.win.close()


if __name__ == "__main__":
    unittest.main()
