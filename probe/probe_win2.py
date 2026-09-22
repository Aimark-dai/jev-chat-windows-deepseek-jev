# -*- coding: utf-8 -*-
"""
P1 门禁探针 v2：分清「UIA 树是空的」还是「树有但没文字」。

v1 的 bug：异常处理把已取到的 name 一起清空，导致误判 FAIL。这版每项独立 try。
v2 还做三件 v1 没做的事：
  1. 打印树的「形状」（每层子节点数），空树 vs 有树没文字能分开
  2. 扫描所有 Weixin.exe 窗口（主窗口 / 消息阅读 / 设置），不只第一个
  3. 除 UIA 原生属性外，也读 LegacyIAccessible（Qt 走 MSAA/IAccessible2 桥）

只读，绝不写：不点击、不输入、不 Invoke、不自动发送、不碰转账/红包。

用法:
    python probe/probe_win2.py
    python probe/probe_win2.py --narrator-hint   # 只打印强制激活的测试步骤
"""
import argparse
import ctypes
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    import uiautomation as auto
except ImportError:
    sys.exit("缺依赖：pip install uiautomation pillow")

WECHAT_EXES = {"weixin.exe", "wechat.exe"}


def exe_of_pid(pid):
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


def safe(fn, default=""):
    """每项独立取值，一项失败不影响其他项——v1 就是栽在这。"""
    try:
        v = fn()
        return v if v is not None else default
    except Exception:
        return default


def node_text(c):
    """返回 (name, value, legacy_name, legacy_value)，四路独立取。"""
    name = safe(lambda: (c.Name or "").strip())
    val = ""
    vp = safe(lambda: c.GetValuePattern(), None)
    if vp is not None:
        val = safe(lambda: (vp.Value or "").strip())
    lname = lval = ""
    lp = safe(lambda: c.GetLegacyIAccessiblePattern(), None)
    if lp is not None:
        lname = safe(lambda: (lp.Name or "").strip())
        lval = safe(lambda: (lp.Value or "").strip())
    return name, val, lname, lval


def walk(c, depth, stats, texts, max_depth=40, cap=8000):
    """收集树形状 + 文字。stats[depth] = 该层节点数。"""
    if stats["total"] >= cap:
        return
    stats["total"] += 1
    stats["by_depth"][depth] = stats["by_depth"].get(depth, 0) + 1

    name, val, lname, lval = node_text(c)
    best = name or val or lname or lval
    if best:
        texts.append((depth,
                      safe(lambda: c.ControlTypeName, "?"),
                      safe(lambda: c.ClassName, "?"),
                      best))

    if depth >= max_depth:
        return
    for ch in safe(lambda: c.GetChildren(), []):
        walk(ch, depth + 1, stats, texts, max_depth, cap)


def has_cn(s):
    return any("一" <= ch <= "鿿" for ch in s)


NARRATOR_HINT = """
--- 如果树是空的，按这个顺序试（都不改微信、不注入）---

1) 开讲述人强制 Qt 激活无障碍（Qt 是懒加载，见到读屏器才填充树）：
       Win + Ctrl + Enter        # 开启讲述人
   然后【重新跑一遍本探针】，看节点数有没有变。跑完再 Win+Ctrl+Enter 关掉。

2) 用微软官方工具交叉验证，排除是我代码的问题：
   Accessibility Insights for Windows (免费)  https://accessibilityinsights.io/
   或 Windows SDK 里的 inspect.exe
   把鼠标悬到微信【聊天气泡】上，看 Inspect 能不能读出文字。
   Inspect 读得到 = UIA 有戏，是我代码问题；Inspect 也读不到 = Qt 无障碍被关了。

3) 若 1、2 都空 → 微信把 Qt 的 accessibility 编译掉/关掉了，UIA 路线到此为止，
   只剩截屏 + 本地 OCR。（注入 Qt 无障碍插件属于 hook，违反非侵入约束，不做。）
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--narrator-hint", action="store_true")
    args = ap.parse_args()
    if args.narrator_hint:
        print(NARRATOR_HINT)
        return

    root = auto.GetRootControl()
    wins = [(w, exe_of_pid(w.ProcessId)) for w in root.GetChildren()]
    targets = [(w, e) for w, e in wins if e.lower() in WECHAT_EXES]
    if not targets:
        sys.exit("没找到 Weixin.exe 窗口。")

    for w, exe in targets:
        title = safe(lambda: w.Name, "")
        print(f"\n{'='*60}")
        print(f"窗口: {title!r}  class={safe(lambda: w.ClassName)}  hwnd={safe(lambda: w.NativeWindowHandle)}")

        stats = {"total": 0, "by_depth": {}}
        texts = []
        walk(w, 0, stats, texts)

        print(f"树: 共 {stats['total']} 个节点")
        print(f"    每层节点数: {dict(sorted(stats['by_depth'].items()))}")
        print(f"    有文字: {len(texts)}   含中文: {sum(1 for t in texts if has_cn(t[3]))}")

        if stats["total"] <= 1:
            print("    >>> 空树：只有窗口本身，没有任何子节点 → 无障碍未激活或被编译掉")
        elif not texts:
            print("    >>> 有树无文字：桥半通，节点存在但文字被挡")
        else:
            print("    --- 前 25 条文字 ---")
            for depth, ct, cls, s in texts[:25]:
                print(f"      d{depth:<2} {ct:18} {cls:22} {s[:40]!r}")

    print(f"\n{'='*60}")
    print("判定看上面每个窗口的 >>> 行。若全是空树，跑：")
    print("    python probe/probe_win2.py --narrator-hint")


if __name__ == "__main__":
    main()
