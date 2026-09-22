# -*- coding: utf-8 -*-
"""生成 docs/icon.ico（打包用的程序图标）：圆角绿底 + 白色 J。
图标已经提交进仓库，只有想换颜色/字母时才需要重跑：python tools/make_icon.py"""
import os

from PIL import Image, ImageDraw, ImageFont

GREEN = "#18794e"
SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "icon.ico")
FONTS = (  # 随手找一个粗体，Mac / Windows / Linux 各一个，都没有就用 Pillow 自带的
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)


def font(px):
    path = next((p for p in FONTS if os.path.exists(p)), None)
    return ImageFont.truetype(path, px) if path else ImageFont.load_default(px)


def main():
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 255, 255), radius=56, fill=GREEN)
    d.text((128, 120), "J", font=font(168), fill="white", anchor="mm")  # anchor=mm：按字形居中，不用自己算 bbox
    img.save(OUT, sizes=SIZES)
    assert os.path.getsize(OUT) > 1024, OUT  # 多尺寸 ico 不可能只有几百字节，真写出来了才算数
    print(f"{OUT}  {os.path.getsize(OUT)} bytes  {len(SIZES)} sizes")


if __name__ == "__main__":
    main()
