# -*- coding: utf-8 -*-
"""macOS WeChat window capture. Frames stay in memory; no screen image is saved."""

from __future__ import annotations

import time

import numpy as np


def _quartz():
    import Quartz

    return Quartz


def window_info(window_id: int | None = None) -> dict | None:
    quartz = _quartz()
    windows = quartz.CGWindowListCopyWindowInfo(
        quartz.kCGWindowListOptionOnScreenOnly | quartz.kCGWindowListExcludeDesktopElements,
        quartz.kCGNullWindowID,
    )
    for info in windows or ():
        if window_id is None:
            owner = str(info.get(quartz.kCGWindowOwnerName) or "").lower()
            bounds = info.get(quartz.kCGWindowBounds) or {}
            if owner not in ("wechat", "微信") or info.get(quartz.kCGWindowLayer) != 0:
                continue
            if bounds.get("Width", 0) < 400 or bounds.get("Height", 0) < 300:
                continue
            return info
        if int(info.get(quartz.kCGWindowNumber, -1)) == window_id:
            return info
    return None


def find_wechat_hwnd() -> int:
    quartz = _quartz()
    info = window_info()
    if info is None:
        raise RuntimeError("未找到可见的 Mac 微信窗口，请打开微信并保持聊天窗口可见。")
    if not quartz.CGPreflightScreenCaptureAccess():
        quartz.CGRequestScreenCaptureAccess()
        if not quartz.CGPreflightScreenCaptureAccess():
            raise RuntimeError("请在 macOS 系统设置中允许本程序录制屏幕，然后重新打开程序。")
    return int(info[quartz.kCGWindowNumber])


def unminimize(_window_id: int) -> bool:
    """macOS does not capture minimized windows; never change the user's focus here."""
    return False


def _frame(window_id: int) -> np.ndarray:
    quartz = _quartz()
    image = quartz.CGWindowListCreateImage(
        quartz.CGRectNull,
        quartz.kCGWindowListOptionIncludingWindow,
        window_id,
        quartz.kCGWindowImageBoundsIgnoreFraming,
    )
    if image is None:
        raise RuntimeError("无法读取微信画面，请检查屏幕录制权限并保持微信窗口可见。")
    width, height = quartz.CGImageGetWidth(image), quartz.CGImageGetHeight(image)
    stride = quartz.CGImageGetBytesPerRow(image)
    if width < 400 or height < 300 or stride < width * 4:
        raise RuntimeError("微信截图尺寸或像素格式无效。")
    raw = bytes(quartz.CGDataProviderCopyData(quartz.CGImageGetDataProvider(image)))
    if len(raw) < stride * height:
        raise RuntimeError("微信截图数据不完整。")
    # CoreGraphics' 32-bit little-endian premultiplied-alpha window images are BGRA.
    pixels = np.frombuffer(raw, dtype=np.uint8, count=stride * height).reshape(height, stride)
    return np.ascontiguousarray(pixels[:, :width * 4].reshape(height, width, 4)[:, :, 2::-1])


class Capture:
    def __init__(self, window_id: int, settle: float = 0.25, max_wait: float = 1.0):
        self.window_id = window_id
        self.settle, self.max_wait = settle, max_wait
        self.shape = self.area = self.last = self.pending = None
        self.t = self.t0 = self._last_sample = 0.0
        self._stopped = False

    def settled(self) -> np.ndarray | None:
        now = time.perf_counter()
        if now - self._last_sample >= 0.15:
            self._last_sample = now
            full = _frame(self.window_id)
            if self.area is None or full.shape != self.shape:
                from .capture import chat_area

                self.shape, self.area = full.shape, chat_area(full)
            if self.area is not None:
                x0, y0, x1, y1 = self.area[:4]
                chat = full[y0:y1, x0:x1]
                if self.last is None or not np.array_equal(chat, self.last):
                    self.last = chat
                    if self.pending is None:
                        self.t0 = now
                    self.pending, self.t = full, now
        if self.pending is None:
            return None
        if now - self.t < self.settle and now - self.t0 < self.max_wait:
            return None
        full, self.pending = self.pending, None
        return full

    def alive(self) -> bool:
        return not self._stopped and window_info(self.window_id) is not None

    def stop(self) -> None:
        self._stopped = True

    def wait(self) -> None:
        pass
