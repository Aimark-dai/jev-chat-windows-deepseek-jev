# -*- coding: utf-8 -*-
"""用合成数据预览 Qt 界面；不采集、不联网、不操作真实微信。

    python tools/preview_ui.py --state ready
    python tools/preview_ui.py --state ready --screenshot docs/ui_home.png

演示设置只保存在内存，不读取真实密钥，也不修改环境变量或 config.json。
"""
from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

from app import settings


_STATES = ("ready", "waiting", "loading", "error", "setup", "settings", "paused", "auto-send")

_CHAT = "白金搬砖小分队"  # 演示里「微信当前开着的」会话：用群聊，回复对象那一行才看得见
# (会话, 谁, 内容, 群里的发言人, 时间)：两个会话，下拉框里都能看到
_MESSAGES = (
    ("白金搬砖小分队", "her", "周末有人去爬山吗", "阿杰", "09:12"),
    ("白金搬砖小分队", "me", "我有空，几点集合？", "", "09:15"),
    ("白金搬砖小分队", "her", "我也去，带上我一个", "陈与小金", "09:15"),
    ("白金搬砖小分队", "her", "八点地铁口见，记得带水", "阿杰", "09:16"),
    (_CHAT, "me", "有空呀，还是上次那家？", "", "18:43"),
    (_CHAT, "her", "好呀！六点见怎么样？我好久没吃了 😋", "", "18:43"),
)
_GROUP = "白金搬砖小分队"
_SENDERS = ("阿杰", "陈与小金")  # 最近说话的排最前，跟 main.py 那边一个口径

_RESULT = {
    "candidates": [
        "周六六点没问题，上次那家见～",
        "可以呀，周六六点在上次那家见！我也有点馋了 😋",
        "好呀，就周六六点！需要我先订个位吗？",
    ],
    # 推荐故意放在第二项，方便检查视觉排序和按钮对应关系。
    "best_index": 1,
    "best_reply": "可以呀，周六六点在上次那家见！我也有点馋了 😋",
    "scores": [0.21, 0.66, 0.13],
    "answers": {
        "literal_question": {"type": "noul", "noul": 0.98},
        "true_intent": {"type": "choice", "choice": "casual_chat"},
        "danger_level": {"type": "score", "score": 0},
        "should_reply_now": {"type": "noul", "noul": 0.96},
        "best_action": {"type": "choice", "choice": "make_plan"},
        "she_needs": {"type": "choice", "choice": "action"},
        "tension_resolved": {"type": "noul", "noul": 0.99},
        "best_reply": {
            "type": "choice", "choice": "reply_b",
            "probabilities": {"reply_a": 0.21, "reply_b": 0.66, "reply_c": 0.13},
        },
    },
    "usage": {},
    "reply_to": "阿杰",  # 跟 _SENDERS[0] 一致，让「回复给 …」那行在演示里看得见
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="用合成聊天预览 Qt UI；绝不采集、联网或填入真实微信。"
    )
    parser.add_argument("--state", choices=_STATES, default="ready", help="预览界面状态")
    parser.add_argument("--screenshot", metavar="PATH", help="将演示界面保存为 PNG 后退出（合成数据，不含微信内容）")
    args = parser.parse_args()
    target = Path(args.screenshot).expanduser() if args.screenshot else None

    demo_settings = {"has_key": args.state != "setup", "relationship": "friends", "context": 10,
                     "has_deepseek_key": False, "has_typesafe_key": args.state != "setup",
                     "draft_provider": "deepseek", "judge_provider": "typesafe", "reply_target": True,
                     "style": "话少，基本不用标点，急了才发感叹号", "thinking": False,
                     "check_update": True, "auto_send": args.state == "auto-send"}

    def save_demo_settings(key, relationship_text, context_n=None,
                           deepseek_key_text=None, draft_provider=None, reply_target_on=None,
                           style_text=None, thinking_on=None, check_update_on=None,
                           auto_send_on=None, typesafe_key_text=None,
                           judge_provider_text=None):
        if key:
            demo_settings["has_key"] = True
        demo_settings["relationship"] = relationship_text
        if context_n is not None:
            demo_settings["context"] = context_n
        if deepseek_key_text:
            demo_settings["has_deepseek_key"] = True
        if draft_provider is not None:
            demo_settings["draft_provider"] = draft_provider
        if reply_target_on is not None:
            demo_settings["reply_target"] = bool(reply_target_on)
        if style_text is not None:
            demo_settings["style"] = style_text
        if thinking_on is not None:
            demo_settings["thinking"] = bool(thinking_on)
        if check_update_on is not None:
            demo_settings["check_update"] = bool(check_update_on)
        if auto_send_on is not None:
            demo_settings["auto_send"] = bool(auto_send_on)
        if typesafe_key_text:
            demo_settings["has_typesafe_key"] = True
        if judge_provider_text is not None:
            demo_settings["judge_provider"] = judge_provider_text

    def set_demo_auto_send(enabled):
        demo_settings["auto_send"] = bool(enabled)

    # 在创建 Overlay 前替换设置接口，整个事件循环期间都保持隔离。
    with patch.multiple(
        settings,
        has_key=lambda: demo_settings["has_key"],
        relationship=lambda: demo_settings["relationship"],
        context=lambda: demo_settings["context"],
        deepseek_key=lambda: "",
        has_deepseek_key=lambda: demo_settings["has_deepseek_key"],
        has_typesafe_key=lambda: demo_settings["has_typesafe_key"],
        draft_provider=lambda: demo_settings["draft_provider"],
        judge_provider=lambda: demo_settings["judge_provider"],
        reply_target=lambda: demo_settings["reply_target"],
        style=lambda: demo_settings["style"],
        thinking=lambda: demo_settings["thinking"],
        check_update=lambda: demo_settings["check_update"],
        auto_send=lambda: demo_settings["auto_send"],
        set_auto_send=set_demo_auto_send,
        save=save_demo_settings,
    ):
        from PySide6.QtCore import QTimer
        from app.overlay import Overlay

        def simulate_fill(text):
            # 等 Overlay 自身的点击反馈结束后，再显示明确的演示提示。
            if args.state != "auto-send":
                QTimer.singleShot(0, lambda: ov.set_status(
                    f"演示模式：已模拟填入「{text}」；未操作微信。", kind="success"
                ))

        # 只有当前会话有结果，切到另一个会话就是空态——跟真实情况一致
        ov = Overlay(on_fill=simulate_fill, result_of=lambda t: _RESULT if t == _CHAT else None)
        ov.win.setWindowTitle("WeChatJev · 界面演示（合成数据）")

        if args.state == "setup":
            ov.set_status("演示模式：请填写示例密钥，设置仅保存在本次预览内。", kind="warning")
            ov.open_settings()
        elif args.state == "waiting":
            ov.set_status("演示模式：等待对方的新消息；当前未连接微信。")
        else:
            for chat, who, text, name, timestamp in _MESSAGES:
                ov.log_message(who, text, name, timestamp=timestamp, chat=chat)
            ov.set_targets(_GROUP, _SENDERS, _SENDERS[0])  # 群聊才有回复对象这一行
            ov.set_chat(_CHAT)
            ov.show(_RESULT)
            ov.set_status("演示模式：已生成 3 条建议，点击填入仅模拟操作。", kind="success")
            ov.set_update("9.9.9", "https://github.com/Aimark-dai/jev-chat-windows-deepseek-jev/releases/latest")
            if args.state == "loading":
                ov.set_busy(True)
                ov.set_status("演示模式：正在为最新消息生成建议…", kind="busy")
            elif args.state == "error":
                ov.set_busy(True)
                ov.set_status("演示模式：分析失败，请检查网络和密钥，等待下一条消息后重试。", kind="error")
            elif args.state == "settings":
                ov.open_settings()
            elif args.state == "paused":
                ov.set_capture(False)
            elif args.state == "auto-send":
                ov.begin_auto_send(_RESULT["best_reply"], lambda: None)

        exit_code = 0
        if target is not None:
            def save_screenshot():
                nonlocal exit_code
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not ov.win.grab().save(str(target), "PNG"):
                        raise OSError(f"无法保存截图：{target}")
                    print(f"已保存合成界面截图：{target}")
                except OSError as exc:
                    print(str(exc))
                    exit_code = 1
                finally:
                    ov.app.quit()

            QTimer.singleShot(500, save_screenshot)
        ov.run()
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
