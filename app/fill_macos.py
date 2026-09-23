# -*- coding: utf-8 -*-
"""Fill and optionally send a Mac WeChat draft after explicit user action."""

from __future__ import annotations

import time

from .capture_macos import window_info


def _frameworks():
    import AppKit
    import Quartz

    return AppKit, Quartz


def set_clipboard(text: str) -> None:
    appkit, _ = _frameworks()
    board = appkit.NSPasteboard.generalPasteboard()
    board.clearContents()
    if not board.setString_forType_(text, appkit.NSPasteboardTypeString):
        raise RuntimeError("无法写入 macOS 剪贴板。")


def _wechat_application(window_id: int):
    appkit, quartz = _frameworks()
    info = window_info(window_id)
    if info is None:
        raise RuntimeError("微信窗口已关闭或最小化。")
    pid = int(info[quartz.kCGWindowOwnerPID])
    app = appkit.NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    if app is None or str(app.localizedName()).lower() not in ("wechat", "微信"):
        raise RuntimeError("目标窗口不是微信，已拒绝输入。")
    return app, info


def _input_point(info: dict, area: tuple[int, int, int, int], window_id: int) -> tuple[float, float]:
    _, quartz = _frameworks()
    image = quartz.CGWindowListCreateImage(
        quartz.CGRectNull, quartz.kCGWindowListOptionIncludingWindow,
        window_id, quartz.kCGWindowImageBoundsIgnoreFraming,
    )
    if image is None:
        raise RuntimeError("无法读取微信窗口位置。")
    bounds = info[quartz.kCGWindowBounds]
    width, height = quartz.CGImageGetWidth(image), quartz.CGImageGetHeight(image)
    if width <= 0 or height <= 0:
        raise RuntimeError("微信窗口尺寸无效。")
    x0, _, _, y1 = area
    return (float(bounds["X"]) + (x0 + 60) * float(bounds["Width"]) / width,
            float(bounds["Y"]) + (y1 + 40) * float(bounds["Height"]) / height)


def _click(point: tuple[float, float]) -> None:
    _, quartz = _frameworks()
    current = quartz.CGEventGetLocation(quartz.CGEventCreate(None))
    for kind in (quartz.kCGEventLeftMouseDown, quartz.kCGEventLeftMouseUp):
        quartz.CGEventPost(
            quartz.kCGHIDEventTap,
            quartz.CGEventCreateMouseEvent(None, kind, point, quartz.kCGMouseButtonLeft),
        )
    quartz.CGEventPost(
        quartz.kCGHIDEventTap,
        quartz.CGEventCreateMouseEvent(None, quartz.kCGEventMouseMoved, current,
                                       quartz.kCGMouseButtonLeft),
    )
    time.sleep(0.05)


def _key(code: int, command: bool = False) -> None:
    _, quartz = _frameworks()
    for down in (True, False):
        event = quartz.CGEventCreateKeyboardEvent(None, code, down)
        if command:
            quartz.CGEventSetFlags(event, quartz.kCGEventFlagMaskCommand)
        quartz.CGEventPost(quartz.kCGHIDEventTap, event)
    time.sleep(0.05)


def fill(window_id: int, area: tuple[int, int, int, int], text: str,
         replace: bool = False) -> None:
    appkit, _ = _frameworks()
    app, info = _wechat_application(window_id)
    set_clipboard(text)
    if not app.activateWithOptions_(appkit.NSApplicationActivateIgnoringOtherApps):
        raise RuntimeError("无法激活微信，请检查 macOS 辅助功能权限。")
    time.sleep(0.15)
    if appkit.NSWorkspace.sharedWorkspace().frontmostApplication().processIdentifier() != app.processIdentifier():
        raise RuntimeError("微信未在前台，已拒绝填入。")
    _click(_input_point(info, area, window_id))
    _key(0x00 if replace else 0x7C, command=True)  # Cmd+A / Cmd+Right
    _key(0x09, command=True)  # Cmd+V


def send(window_id: int, area: tuple[int, int, int, int]) -> None:
    appkit, _ = _frameworks()
    app, info = _wechat_application(window_id)
    if appkit.NSWorkspace.sharedWorkspace().frontmostApplication().processIdentifier() != app.processIdentifier():
        raise RuntimeError("微信已不在前台，已取消自动发送。")
    _click(_input_point(info, area, window_id))
    _key(0x24)  # Return; only called after the explicit countdown gate.
