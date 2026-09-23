# -*- coding: utf-8 -*-
"""微信输入操作：填入候选，以及用户明确开启后的倒计时发送。"""
import ctypes
import ctypes.wintypes as w
import sys
import time

u32, k32 = ((ctypes.windll.user32, ctypes.windll.kernel32)
            if sys.platform == "win32" else (None, None))

# 64 位下 ctypes.windll 默认 restype 是 32 位 c_int，而 GlobalAlloc 返回 64 位 HGLOBAL——
# 不声明类型句柄会被截断成垃圾值，GlobalLock(垃圾) 返回 NULL，memmove(NULL,…) 就是
# "access violation writing 0x0"。所有带句柄/指针的函数必须显式声明。
if sys.platform == "win32":
    k32.GlobalAlloc.restype = ctypes.c_void_p
    k32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalLock.argtypes = [ctypes.c_void_p]
    k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    k32.GlobalFree.argtypes = [ctypes.c_void_p]
    u32.SetClipboardData.restype = ctypes.c_void_p
    u32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]


def set_clipboard(text):
    """写剪贴板。剪贴板可能被别的程序占着（剪贴板管理器、截图工具），重试几次。"""
    data = text.encode("utf-16-le") + b"\0\0"
    for attempt in range(10):
        if not u32.OpenClipboard(None):
            time.sleep(0.05)
            continue
        try:
            u32.EmptyClipboard()
            h = k32.GlobalAlloc(0x2, len(data))  # GMEM_MOVEABLE
            if not h:
                raise RuntimeError("GlobalAlloc 失败")
            p = k32.GlobalLock(h)
            if not p:
                k32.GlobalFree(h)
                raise RuntimeError("GlobalLock 失败")
            ctypes.memmove(p, data, len(data))
            k32.GlobalUnlock(h)
            if not u32.SetClipboardData(13, h):  # CF_UNICODETEXT；成功后句柄归系统，不能 Free
                k32.GlobalFree(h)
                raise RuntimeError(f"SetClipboardData 失败 (attempt {attempt})")
            return
        finally:
            u32.CloseClipboard()
    raise RuntimeError("OpenClipboard 连续失败，剪贴板被其他程序占用")


def _input_point(hwnd, area):
    r = w.RECT()
    if ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(r), ctypes.sizeof(r)) != 0:
        u32.GetWindowRect(hwnd, ctypes.byref(r))
    x0, _, _, y1 = area
    return r.left + x0 + 60, r.top + y1 + 40


def _click_input(hwnd, area):
    cx, cy = _input_point(hwnd, area)
    old = w.POINT()
    u32.GetCursorPos(ctypes.byref(old))
    u32.SetCursorPos(cx, cy)
    time.sleep(0.05)
    u32.mouse_event(0x2, 0, 0, 0, 0)
    u32.mouse_event(0x4, 0, 0, 0, 0)
    time.sleep(0.05)
    u32.SetCursorPos(old.x, old.y)


def fill(hwnd, area, text, replace=False):
    """area = 消息区 (x0, y0, x1, y1)。replace=True 用于自动发送，避免把旧草稿一起发出。"""
    from app.capture import unminimize

    set_clipboard(text)
    unminimize(hwnd)

    # SetForegroundWindow 有前台窗口保护，普通后台进程会被拒；AttachThreadInput 绕过
    fg = u32.GetForegroundWindow()
    if fg != hwnd:
        fg_tid = u32.GetWindowThreadProcessId(fg, None)
        our_tid = k32.GetCurrentThreadId()
        u32.AttachThreadInput(our_tid, fg_tid, True)
        u32.SetForegroundWindow(hwnd)
        u32.AttachThreadInput(our_tid, fg_tid, False)
        time.sleep(0.15)  # 给微信一点时间响应前台切换

    _click_input(hwnd, area)
    time.sleep(0.05)
    # 手动填入追加到末尾；自动发送必须先全选替换，不允许夹带用户未完成的草稿。
    u32.keybd_event(0x11, 0, 0, 0)  # Ctrl 按下
    target_key = 0x41 if replace else 0x23  # A / End
    u32.keybd_event(target_key, 0, 0, 0)
    u32.keybd_event(target_key, 0, 2, 0)
    u32.keybd_event(0x11, 0, 2, 0)  # Ctrl 抬起
    time.sleep(0.05)
    u32.keybd_event(0x11, 0, 0, 0)  # Ctrl
    u32.keybd_event(0x56, 0, 0, 0)  # V
    u32.keybd_event(0x56, 0, 2, 0)
    u32.keybd_event(0x11, 0, 2, 0)
    # 到此为止。手动模式下不发；自动模式由界面倒计时后单独调 send。


def send(hwnd, area):
    """将已填入的内容按回车发送。微信不在前台时拒绝操作，避免发到别处。"""
    if u32.GetForegroundWindow() != hwnd:
        raise RuntimeError("微信已不在前台")
    _click_input(hwnd, area)
    time.sleep(0.05)
    u32.keybd_event(0x0D, 0, 0, 0)  # Enter 按下
    u32.keybd_event(0x0D, 0, 2, 0)  # Enter 抬起


if sys.platform == "darwin":
    from .fill_macos import fill, send, set_clipboard
