# -*- coding: utf-8 -*-
"""端到端冒烟：截图里那段真实对话跑一遍完整链，打印判断 + 排好序的候选。

    set DEEPSEEK_API_KEY=...   (Windows)
    export DEEPSEEK_API_KEY=...(mac/Linux)
    python tools/demo.py

起草想走 DeepSeek 直连就把下面 PROVIDER 改成 "deepseek"，并设好 DEEPSEEK_API_KEY。
"""
from __future__ import annotations

import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from core.engine import analyze
from core.jev_client import JevError

MESSAGES = [
    ("her", "你今天是不是又忘了我跟你说过什么？"),
    ("me", "记得，你先别提示我，让我自己说。"),
    ("her", "那你说。"),
    ("me", "等一下，我想说完整一点。"),
    ("her", "你最好是。"),
]
RELATIONSHIP = "romantic partners"
PROVIDER = "deepseek"


def fmt(name: str, ans: dict) -> str:
    t = ans.get("type")
    if t == "noul":
        return f"{name}: {ans.get('noul'):.2f}"
    if t == "choice":
        return f"{name}: {ans.get('choice')} (conf {ans.get('confidence'):.2f})"
    if t == "score":
        return f"{name}: {ans.get('score'):.1f}/9 (conf {ans.get('confidence'):.2f})"
    return f"{name}: {ans}"


def main() -> int:
    print("对话:")
    for w, t in MESSAGES:
        print(f"  {w}: {t}")
    try:
        r = analyze(MESSAGES, RELATIONSHIP, provider=PROVIDER)
    except JevError as e:
        print(f"\n失败: {e}")
        return 1

    print("\n判断:")
    for name in ("literal_question", "true_intent", "danger_level",
                 "should_reply_now", "best_action", "she_needs", "tension_resolved"):
        if name in r["answers"]:
            print("  " + fmt(name, r["answers"][name]))

    print("\n候选（Jev 排序，★ = 推荐）:")
    scores = r.get("scores")
    for i, c in enumerate(r["candidates"]):
        pct = f"  {scores[i]:.0%}" if scores else ""
        print(f"  {'★' if i == r['best_index'] else ' '} {c}{pct}")

    u = r["usage"]
    if u:
        print(f"\nusage: in={u.get('input_tokens')} out={u.get('output_tokens')} "
              f"cost=${u.get('cost')}")
    print("\n期望核对: true_intent≈confirm_you_care, best_action≈check_history, danger_level 中高档")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
