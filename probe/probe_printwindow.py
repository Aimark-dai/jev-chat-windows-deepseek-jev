# -*- coding: utf-8 -*-
"""
PrintWindow 探针：不用 WGC（Win10 上有黄框关不掉），试 PrintWindow + PW_RENDERFULLCONTENT 对 Weixin.exe 出不出图。
后台/被遮挡都能截，只要没最小化；纯 ctypes，零依赖。IDE 里直接 Run，弹窗看图，黑的就是不行。

只读，帧只在内存，不写盘。
"""
import ctypes
import ctypes.wintypes as w
import os
import time
import tkinter as tk

import numpy as np
from PIL import Image, ImageTk

u32, g32 = ctypes.windll.user32, ctypes.windll.gdi32
for fn in (u32.GetDC, u32.GetWindowDC, g32.CreateCompatibleDC, g32.CreateDIBSection, g32.SelectObject):
    fn.restype = ctypes.c_void_p  # 64 位句柄别被截成 int
g32.SelectObject.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
g32.DeleteObject.argtypes = g32.DeleteDC.argtypes = (ctypes.c_void_p,)
u32.ReleaseDC.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
u32.PrintWindow.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint)


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", w.DWORD), ("biWidth", w.LONG), ("biHeight", w.LONG), ("biPlanes", w.WORD),
                ("biBitCount", w.WORD), ("biCompression", w.DWORD), ("biSizeImage", w.DWORD),
                ("biXPelsPerMeter", w.LONG), ("biYPelsPerMeter", w.LONG), ("biClrUsed", w.DWORD), ("biClrImportant", w.DWORD)]


def find_wechat_hwnd():
    k32 = ctypes.windll.kernel32
    found = []

    def exe_of(pid):
        h = k32.OpenProcess(0x1000, False, pid)
        if not h:
            return ""
        buf, size = ctypes.create_unicode_buffer(1024), ctypes.c_uint(1024)
        ok = k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
        k32.CloseHandle(h)
        return os.path.basename(buf.value).lower() if ok else ""

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        if not u32.IsWindowVisible(hwnd):
            return True
        pid = ctypes.c_ulong()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if exe_of(pid.value) in ("weixin.exe", "wechat.exe"):
            title = ctypes.create_unicode_buffer(256)
            u32.GetWindowTextW(hwnd, title, 256)
            found.append((hwnd, title.value))
        return True

    u32.EnumWindows(cb, 0)
    assert found, "没找到微信窗口"
    return next((h for h, t in found if t == "微信"), found[0][0])


def grab(hwnd, flags=3):
    """PrintWindow 到内存 DIB → numpy RGB。flags: 1=PW_CLIENTONLY, 2=PW_RENDERFULLCONTENT。"""
    r = w.RECT()
    u32.GetClientRect(hwnd, ctypes.byref(r))
    W, H = r.right, r.bottom
    hdc = u32.GetDC(hwnd)
    mdc = g32.CreateCompatibleDC(hdc)
    bmi = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), W, -H, 1, 32, 0)  # 负高 = 自上而下
    bits = ctypes.c_void_p()
    hbm = g32.CreateDIBSection(hdc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
    old = g32.SelectObject(mdc, hbm)
    ok = u32.PrintWindow(hwnd, mdc, flags)
    arr = np.frombuffer(ctypes.string_at(bits, W * H * 4), np.uint8).reshape(H, W, 4)[:, :, 2::-1].copy()  # BGRA→RGB
    g32.SelectObject(mdc, old)
    g32.DeleteObject(hbm)
    g32.DeleteDC(mdc)
    u32.ReleaseDC(hwnd, hdc)
    return arr, ok


u32.SetProcessDPIAware()
hwnd = find_wechat_hwnd()
for flags, name in ((3, "PW_CLIENTONLY|PW_RENDERFULLCONTENT"), (2, "PW_RENDERFULLCONTENT"), (0, "普通 PrintWindow")):
    arr, ok = grab(hwnd, flags)
    t0 = time.perf_counter()
    for _ in range(10):
        grab(hwnd, flags)
    ms = (time.perf_counter() - t0) * 100
    black = arr.max() == 0 or arr.std() < 2
    print(f"{name:<36} ok={ok} {arr.shape[1]}x{arr.shape[0]}  {ms:5.1f} ms/帧  {'>>> 黑屏/纯色，不行' if black else '有内容'}")
    if not black:
        break

img = Image.fromarray(arr)
img.thumbnail((1400, 900))
root = tk.Tk()
root.title(f"PrintWindow flags={flags}，看是不是微信当前画面（把微信遮住再跑一次试后台）")
photo = ImageTk.PhotoImage(img)
tk.Label(root, image=photo).pack()
root.mainloop()
