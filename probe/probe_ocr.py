# -*- coding: utf-8 -*-
"""
P2 门禁探针：OCR 读不读得准微信聊天气泡，左右说话人分不分得开。

UIA 已证伪（微信 4.x 自绘到 MMUIRenderSubWindowHW 单块 GPU 画布，无控件树），
剩下唯一的非侵入采集手段就是截屏 + 本地 OCR。这个探针回答两件事：
  1. 中文气泡文字 OCR 准确率够不够用
  2. 能不能靠 x 坐标把「我说的」和「对方说的」分开

只读，绝不写。图片只在本地处理，不上传。

用法:
    pip install rapidocr-onnxruntime pillow
    python probe/probe_ocr.py wechat_probe.png
"""
import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:
    sys.exit("缺依赖：pip install rapidocr-onnxruntime pillow")

from PIL import Image


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "wechat_probe.png"
    img = Image.open(path)
    W, H = img.size
    print(f"图片: {path}  {W}x{H}")

    engine = RapidOCR()
    t0 = time.time()
    result, _ = engine(path)
    ms = int((time.time() - t0) * 1000)

    if not result:
        print(">>> OCR 没识别到任何文字。换张带聊天内容的截图再试。")
        return

    print(f"\nOCR 耗时 {ms} ms，识别到 {len(result)} 段文字\n")
    print(f"{'x中心':>6} {'占宽':>5} {'猜':>4} {'置信':>5}  文本")
    print("-" * 70)

    # ponytail: 纯 x 中心阈值分左右，够用就不上气泡颜色聚类。
    # 天花板：头像/系统提示/时间戳会误判，真做采集时要按气泡背景色过滤。
    for box, text, score in result:
        xs = [p[0] for p in box]
        xc = (min(xs) + max(xs)) / 2
        ratio = xc / W
        who = "me" if ratio > 0.55 else ("her" if ratio < 0.45 else "?")
        print(f"{xc:6.0f} {ratio:5.2f} {who:>4} {score:5.2f}  {text[:40]}")

    lows = [r for r in result if r[2] < 0.8]
    print("-" * 70)
    print(f"低置信(<0.80) 段数: {len(lows)} / {len(result)}")
    print("\n>>> 自己核对上面文本跟截图里的气泡对不对得上：")
    print("    文字基本对 + 左右基本分得开  -> OCR 路线可行，继续往下做")
    print("    文字错漏多                   -> 换 PaddleOCR 或只 OCR 聊天区裁剪图")


if __name__ == "__main__":
    main()
