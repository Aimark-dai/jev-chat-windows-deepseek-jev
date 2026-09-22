import unittest
from unittest.mock import Mock, patch

import main
from app import fill as fill_module
from app.overlay import Overlay


class _FakeUser32:
    def __init__(self, foreground):
        self.foreground = foreground
        self.keys = []

    def GetForegroundWindow(self):
        return self.foreground

    def keybd_event(self, key, scan, flags, extra):
        self.keys.append((key, flags))


class AutoSendTests(unittest.TestCase):
    def test_auto_send_requires_jev_quality_gate_to_pass(self):
        self.assertTrue(main.can_auto_send({"best_reply": "可以", "quality_passed": True}))
        self.assertTrue(main.can_auto_send({"best_reply": "兼容旧结果"}))
        self.assertFalse(main.can_auto_send({"best_reply": "不合格", "quality_passed": False}))
        self.assertFalse(main.can_auto_send({"best_reply": ""}))

    def test_auto_fill_replaces_existing_draft(self):
        fake = _FakeUser32(foreground=123)
        with patch.object(fill_module, "u32", fake):
            with patch.object(fill_module, "set_clipboard"):
                with patch.object(fill_module, "_click_input"):
                    with patch("app.capture.unminimize"):
                        with patch.object(fill_module.time, "sleep"):
                            fill_module.fill(123, (0, 0, 10, 10), "新回复", replace=True)

        self.assertEqual(fake.keys[:4], [(0x11, 0), (0x41, 0), (0x41, 2), (0x11, 2)])

    def test_cancel_countdown_clears_callback_and_hides_bar(self):
        overlay = Overlay.__new__(Overlay)
        overlay._auto_callback = lambda: None
        overlay._auto_remaining = 3
        overlay._auto_timer = Mock()
        overlay.autoSendBar = Mock()
        overlay.set_status = Mock()

        self.assertTrue(overlay.cancel_auto_send("已取消"))
        self.assertIsNone(overlay._auto_callback)
        self.assertEqual(overlay._auto_remaining, 0)
        overlay._auto_timer.stop.assert_called_once()
        overlay.autoSendBar.hide.assert_called_once()
        overlay.set_status.assert_called_once_with("已取消", "warning")

    def test_send_presses_enter_only_when_wechat_is_foreground(self):
        fake = _FakeUser32(foreground=123)
        with patch.object(fill_module, "u32", fake):
            with patch.object(fill_module, "_click_input") as click:
                with patch.object(fill_module.time, "sleep"):
                    fill_module.send(123, (0, 0, 10, 10))

        click.assert_called_once_with(123, (0, 0, 10, 10))
        self.assertEqual(fake.keys, [(0x0D, 0), (0x0D, 2)])

    def test_send_refuses_when_another_window_is_foreground(self):
        fake = _FakeUser32(foreground=999)
        with patch.object(fill_module, "u32", fake):
            with self.assertRaisesRegex(RuntimeError, "微信已不在前台"):
                fill_module.send(123, (0, 0, 10, 10))
        self.assertEqual(fake.keys, [])

    def test_final_gate_rejects_changed_chat_or_revision(self):
        original_state = dict(main.state)
        original_chats = dict(main.chats)
        try:
            main.chats.clear()
            main.state.update({"hwnd": 123, "area": (0, 0, 10, 10), "chat": "A"})
            main.chat_of("A")["rev"] = 2
            with patch.object(main, "send_reply") as send:
                main.auto_send_reply("A", 2)
                send.assert_called_once()
                with self.assertRaisesRegex(RuntimeError, "其他会话"):
                    main.auto_send_reply("B", 2)
                with self.assertRaisesRegex(RuntimeError, "新消息"):
                    main.auto_send_reply("A", 1)
        finally:
            main.state.clear()
            main.state.update(original_state)
            main.chats.clear()
            main.chats.update(original_chats)


if __name__ == "__main__":
    unittest.main()
