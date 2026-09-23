import os
import queue
import unittest
from collections import deque
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import main
from PySide6.QtWidgets import QApplication, QWidget
from qfluentwidgets import EditableComboBox

from app.overlay import Overlay
from core.typesafe_client import TypeSafeAccessDenied


class ReplyTargetTests(unittest.TestCase):
    def setUp(self):
        self.saved_chats = main.chats.copy()
        self.saved_state = main.state.copy()
        main.chats.clear()
        main.state.update({"busy": False, "rerun": None, "typesafe_blocked": False})

    def tearDown(self):
        main.chats.clear()
        main.chats.update(self.saved_chats)
        main.state.clear()
        main.state.update(self.saved_state)

    def test_manual_target_is_used_even_when_ocr_did_not_find_that_name(self):
        chat = main.chat_of("项目群")
        chat["senders"] = ["识别错的名字"]
        chat["history"] = deque([("her", "有一张要到期了", "识别错的名字")])
        with patch.object(main, "start_analyze") as analyze:
            main.on_target_change("项目群", "张三")

        self.assertEqual(main.target_of("项目群"), "张三")
        analyze.assert_called_once()

        chat["senders"] = ["另一位群成员"]
        self.assertEqual(main.target_of("项目群"), "张三")

    def test_manual_target_is_used_when_filling_wechat(self):
        main.chat_of("项目群")["target"] = "张三"
        main.state.update({"hwnd": 123, "area": (0, 0, 10, 10)})
        fake_overlay = Mock()
        fake_overlay.current_chat.return_value = "项目群"
        fake_overlay.at_prefix_enabled.return_value = True
        with patch.object(main, "ov", fake_overlay, create=True), \
             patch.object(main.settings, "reply_target", return_value=True), \
             patch.object(main, "fill") as fill:
            main.fill_reply("收到")
        fill.assert_called_once_with(123, (0, 0, 10, 10), "@张三 收到", replace=False)

    def test_failed_generation_clears_cached_suggestions_for_current_chat(self):
        chat = main.chat_of("项目群")
        chat["rev"] = 3
        chat["result"] = {"candidates": ["过期建议"]}
        fake_overlay = Mock()
        fake_overlay.current_chat.return_value = "项目群"
        pending = queue.Queue()
        pending.put(("err", "分析失败: 网络超时", "项目群", 3))

        with patch.object(main, "ov", fake_overlay, create=True), \
             patch.object(main, "results", pending), \
             patch.object(main, "update_result", queue.Queue()), \
             patch.object(main, "drain"):
            main.tick()

        self.assertIsNone(chat["result"])
        fake_overlay.show_cached.assert_called_once_with(None)
        fake_overlay.set_status.assert_any_call(
            "生成失败，请检查网络和服务设置；新消息到来后会重试。", "error"
        )

    def test_typesafe_access_denial_stops_automatic_retries_but_deepseek_can_run(self):
        chat = main.chat_of("项目群")
        chat["rev"] = 3
        chat["result"] = {"best_reply": "过期建议"}
        main.state["rerun"] = ("项目群", [("her", "新消息", "张三")])
        fake_overlay = Mock()
        fake_overlay.current_chat.return_value = "项目群"
        pending = queue.Queue()
        pending.put(("blocked", "分析失败: TypeSafe JEV HTTP 403 / Cloudflare 1010", "项目群", 2))

        with patch.object(main, "ov", fake_overlay, create=True), \
             patch.object(main, "results", pending), \
             patch.object(main, "update_result", queue.Queue()), \
             patch.object(main, "drain"):
            main.tick()
            self.assertTrue(main.state["typesafe_blocked"])
            self.assertIsNone(main.state["rerun"])
            self.assertIsNone(chat["result"])
            fake_overlay.show_cached.assert_called_once_with(None)
            fake_overlay.set_status.assert_any_call(main.TYPESAFE_BLOCKED_STATUS, "error")

            with patch.object(main.settings, "judge_provider", return_value="typesafe"), \
                 patch.object(main.threading, "Thread") as thread:
                main.start_analyze("项目群", [("her", "新消息", "张三")])
                thread.assert_not_called()

            with patch.object(main.settings, "judge_provider", return_value="deepseek"), \
                 patch.object(main.settings, "has_key", return_value=True), \
                 patch.object(main.settings, "reply_target", return_value=False), \
                 patch.object(main.threading, "Thread") as thread:
                main.start_analyze("项目群", [("her", "新消息", "张三")])
                thread.assert_called_once()

    def test_background_analysis_classifies_typesafe_access_denial(self):
        pending = queue.Queue()
        with patch.object(main, "results", pending), \
             patch.object(main, "analyze", side_effect=TypeSafeAccessDenied("blocked", 403)):
            main.analyze_bg([("her", "在吗", None)], "项目群", 1)
        kind, message, title, revision = pending.get_nowait()
        self.assertEqual((kind, title, revision), ("blocked", "项目群", 1))
        self.assertIn("blocked", message)

    def test_reply_target_can_be_typed_when_ocr_found_no_senders(self):
        app = QApplication.instance() or QApplication([])
        overlay = Overlay.__new__(Overlay)
        overlay._shown = "项目群"
        overlay._current = False
        overlay.targets = {"项目群": ([], None)}
        overlay.targetRow = QWidget()
        overlay.targetBox = EditableComboBox()
        overlay.on_target_change = Mock()
        overlay.invalidate_replies = Mock()
        overlay.set_status = Mock()
        overlay.targetBox.textEdited.connect(overlay._on_target_editing)
        overlay.targetBox.returnPressed.connect(
            lambda: overlay._on_target_selected(overlay.targetBox.currentText())
        )

        with patch("app.overlay.settings.reply_target", return_value=True):
            overlay._render_targets()
        overlay.targetBox.setText("张三")
        overlay.targetBox.textEdited.emit("张三")
        overlay.invalidate_replies.assert_called_once()
        overlay.targetBox.returnPressed.emit()

        self.assertEqual(overlay.targets["项目群"][1], "张三")
        overlay.on_target_change.assert_called_once_with("项目群", "张三")
        overlay.on_target_change.reset_mock()
        with patch("app.overlay.settings.reply_target", return_value=True):
            overlay._render_targets()
        self.assertEqual(overlay.targetBox.currentText(), "张三")
        overlay._on_target_selected("自动（最近发言人）")
        self.assertIsNone(overlay.targets["项目群"][1])
        overlay.on_target_change.assert_called_once_with("项目群", None)
        overlay.targetBox.close()
        overlay.targetRow.close()


if __name__ == "__main__":
    unittest.main()
