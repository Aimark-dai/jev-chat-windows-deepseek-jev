# -*- coding: utf-8 -*-
"""
P1 门禁探针：微信 Windows 4.x 能不能用 UIA 读到聊天文字，还是必须 OCR？

只读，绝不写：不点击、不输入、不 Invoke、不自动发送、不碰转账/红包。
截图只存本地当前目录，不上传。

用法（Windows，Python 3.9+）:
    pip install uiautomation pillow
    python probe_win.py            # 自动找微信窗口
    python probe_win.py --pick 3   # 列表里手动指定第几个顶层窗口
    python probe_win.py --list     # 只列出所有顶层窗口，不 dump

结论怎么看:
    PASS-A -> 文本节点 > 20 且含中文  -> 走路线 A（UIA 实时文字，毫秒级）
    FAIL   -> 文本节点 <= 3 或全空    -> 走路线 B（截屏 + 本地 OCR，约 0.5s）
"""
import argparse
import ctypes
import io
import os
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    import uiautomation as auto
except ImportError:
    sys.exit("缺依赖：pip install uiautomation pillow")

WECHAT_EXES = {"weixin.exe", "wechat.exe"}  # 4.0 是 Weixin.exe，3.x 是 WeChat.exe


def exe_of_pid(pid):
    """从 pid 拿进程 exe 名，纯 ctypes，不装 psutil。拿不到就返回空串。"""
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = ctypes.c_uint(1024)
        if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return os.path.basename(buf.value)
        return ""
    finally:
        k32.CloseHandle(h)


def top_windows():
    """所有顶层窗口 (control, exe)。"""
    root = auto.GetRootControl()
    out = []
    for w in root.GetChildren():
        out.append((w, exe_of_pid(w.ProcessId)))
    return out


def dump(control, out, depth=0, max_depth=40, cap=6000):
    """递归收集有文字的节点：(depth, ControlTypeName, Name, Value)。cap 防跑飞。"""
    if len(out) >= cap:
        return
    try:
        name = (control.Name or "").strip()
        val = ""
        vp = control.GetValuePattern() if control.IsValuePatternAvailable() else None
        if vp:
            val = (vp.Value or "").strip()
    except Exception:
        name, val = "", ""
    if name or val:
        out.append((depth, control.ControlTypeName, name, val))
    if depth < max_depth:
        for c in control.GetChildren():
            dump(c, out, depth + 1, max_depth, cap)


def has_chinese(s):
    return any("一" <= ch <= "鿿" for ch in s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pick", type=int, help="手动指定第几个顶层窗口（从 --list 看序号）")
    ap.add_argument("--list", action="store_true", help="只列窗口不 dump")
    args = ap.parse_args()

    wins = top_windows()
    print("=== 顶层窗口 ===")
    for i, (w, exe) in enumerate(wins):
        print(f"[{i:2}] exe={exe or '?':16} class={w.ClassName:28} name={w.Name!r}")
    if args.list:
        return

    if args.pick is not None:
        target = wins[args.pick][0]
    else:
        cands = [w for w, exe in wins if exe.lower() in WECHAT_EXES]
        if not cands:
            sys.exit("没自动找到微信窗口。先把微信停在某个聊天窗口，或用 --pick 手动指定。")
        target = cands[0]

    print(f"\n=== 目标窗口: class={target.ClassName} name={target.Name!r} ===")

    # 截图（路线 B 可行性 + 之后喂 OCR 用）。先激活窗口再抓屏。
    try:
        target.SetActive()
        time.sleep(0.4)
        r = target.BoundingRectangle
        from PIL import ImageGrab
        img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom))
        shot = os.path.abspath("wechat_probe.png")
        img.save(shot)
        print(f"截图已存: {shot}  ({img.width}x{img.height})")
    except Exception as e:
        print(f"截图失败: {e}")

    # UIA dump
    t0 = time.time()
    nodes = []
    dump(target, nodes)
    ms = int((time.time() - t0) * 1000)
    texts = [n for n in nodes if n[2] or n[3]]
    cn = [n for n in texts if has_chinese(n[2]) or has_chinese(n[3])]

    print(f"\n=== UIA 结果（{ms} ms）===")
    print(f"有文字节点: {len(texts)}  含中文: {len(cn)}")
    print("--- 前 20 条含中文文本 ---")
    for depth, ct, name, val in cn[:20]:
        s = (name or val).replace("\n", " ")[:40]
        print(f"  d{depth:<2} {ct:16} {s}")

    verdict = "PASS-A (走 UIA 实时文字)" if len(cn) > 20 else "FAIL (走 OCR 路线 B)"
    print(f"\n>>> 判定: {verdict}")


if __name__ == "__main__":
    main()
