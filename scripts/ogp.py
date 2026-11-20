"""SNSで共有したときに出る画像（1200×630）を作る。"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
RED = (255, 0, 51)
INK = (22, 24, 29)
SUB = (100, 106, 115)
FONT_DIRS = [Path("/usr/share/fonts/opentype/noto"), Path("/usr/share/fonts/truetype/noto")]


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    for d in FONT_DIRS:
        p = d / f"NotoSansCJK-{weight}.ttc"
        if p.exists():
            return ImageFont.truetype(str(p), size, index=0)  # index 0 が日本語
    raise FileNotFoundError("Noto Sans CJK が見つかりません（fonts-noto-cjk を入れてください）")


def wrap(draw: ImageDraw.ImageDraw, text: str, f, width: int, max_lines: int) -> list[str]:
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=f) > width:
            lines.append(cur)
            cur = ch
            if len(lines) == max_lines:
                break
        else:
            cur += ch
    else:
        lines.append(cur)
        return lines
    lines[-1] = lines[-1][:-1] + "…"
    return lines


def make(path: Path, headline: str, meta: str, badge: str = "") -> None:
    img = Image.new("RGB", (W, H), (244, 245, 247))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((40, 40, W - 40, H - 40), radius=32, fill="white")
    # ロゴ
    d.rounded_rectangle((90, 90, 130, 118), radius=8, fill=RED)
    d.text((146, 84), "ひらつか議会", font=font("Bold", 30), fill=INK)
    d.text((146 + d.textlength("ひらつか議会 ", font=font("Bold", 30)), 84), "わかる版", font=font("Bold", 30), fill=RED)
    y = 165
    if badge:
        bf = font("Bold", 28)
        bw = d.textlength(badge, font=bf)
        d.rounded_rectangle((90, y, 90 + bw + 36, y + 48), radius=10, fill=(255, 240, 243))
        d.text((108, y + 5), badge, font=bf, fill=(196, 0, 42))
        y += 72
    hf = font("Bold", 54)
    for line in wrap(d, headline, hf, W - 180, 4 if not badge else 3):
        d.text((90, y), line, font=hf, fill=INK)
        y += 74
    mf = font("Regular", 28)
    d.text((90, H - 110), wrap(d, meta, mf, W - 180, 1)[0], font=mf, fill=SUB)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)
