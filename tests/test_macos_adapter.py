import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from app import capture_macos, fill_macos, settings


class MacAdapterTests(unittest.TestCase):
    def test_window_discovery_rejects_missing_wechat_before_permission_prompt(self):
        quartz = Mock()
        with patch.object(capture_macos, "_quartz", return_value=quartz), \
             patch.object(capture_macos, "window_info", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "未找到可见"):
                capture_macos.find_wechat_hwnd()
        quartz.CGRequestScreenCaptureAccess.assert_not_called()

    def test_window_discovery_requires_screen_recording_permission(self):
        quartz = Mock()
        quartz.kCGWindowNumber = "id"
        quartz.CGPreflightScreenCaptureAccess.return_value = False
        with patch.object(capture_macos, "_quartz", return_value=quartz), \
             patch.object(capture_macos, "window_info", return_value={"id": 42}):
            with self.assertRaisesRegex(RuntimeError, "录制屏幕"):
                capture_macos.find_wechat_hwnd()
        quartz.CGRequestScreenCaptureAccess.assert_called_once()

    def test_window_frame_converts_coregraphics_bgra_to_rgb(self):
        quartz = Mock()
        quartz.CGImageGetWidth.return_value = 400
        quartz.CGImageGetHeight.return_value = 300
        quartz.CGImageGetBytesPerRow.return_value = 1600
        data = bytearray(1600 * 300)
        data[:4] = bytes((1, 2, 3, 255))
        quartz.CGDataProviderCopyData.return_value = bytes(data)
        with patch.object(capture_macos, "_quartz", return_value=quartz):
            frame = capture_macos._frame(42)
        self.assertEqual(frame.shape, (300, 400, 3))
        self.assertEqual(frame[0, 0].tolist(), [3, 2, 1])

    def test_capture_settles_changed_chat_without_writing_frames(self):
        capture = capture_macos.Capture(42)
        frame = np.zeros((400, 500, 3), dtype=np.uint8)
        area = (100, 50, 400, 300, np.array([0, 0, 0]), 0)
        with patch.object(capture_macos, "_frame", return_value=frame), \
             patch("app.capture.chat_area", return_value=area), \
             patch.object(capture_macos.time, "perf_counter", side_effect=(1.0, 1.4)):
            self.assertIsNone(capture.settled())
            self.assertIs(capture.settled(), frame)

    def test_send_refuses_if_wechat_is_not_frontmost(self):
        app = SimpleNamespace(processIdentifier=lambda: 123)
        front = SimpleNamespace(processIdentifier=lambda: 999)
        workspace = SimpleNamespace(frontmostApplication=lambda: front)
        appkit = SimpleNamespace(NSWorkspace=SimpleNamespace(sharedWorkspace=lambda: workspace))
        with patch.object(fill_macos, "_frameworks", return_value=(appkit, Mock())), \
             patch.object(fill_macos, "_wechat_application", return_value=(app, {})), \
             patch.object(fill_macos, "_click") as click:
            with self.assertRaisesRegex(RuntimeError, "不在前台"):
                fill_macos.send(42, (0, 0, 10, 10))
        click.assert_not_called()

    def test_mac_preview_never_enables_auto_send(self):
        with patch.object(settings.sys, "platform", "darwin"):
            self.assertFalse(settings.auto_send())
            with self.assertRaisesRegex(RuntimeError, "暂不支持自动发送"):
                settings.set_auto_send(True)


if __name__ == "__main__":
    unittest.main()
