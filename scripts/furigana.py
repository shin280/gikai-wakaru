"""漢字にふりがな（ruby）を付ける。小学生モードで表示する。

読みは rt の data-r に入れ、CSS で表示する（検索エンジンが本文を「機能きのう」のように読まないため）。

読みは形態素解析（fugashi + unidic-lite）で自動で付けるので、
地名・人名などで読みが違うことがある。
"""
import re
from functools import lru_cache

try:
    import fugashi
    _TAGGER = fugashi.Tagger()
except Exception:  # 入っていなければ、ふりがなは付けない
    _TAGGER = None

KANJI = re.compile(r"[㐀-鿿々]")
SPLIT = re.compile(r"(<script\b.*?</script>|<style\b.*?</style>|<textarea\b.*?</textarea>|<!--.*?-->|<[^>]+>)", re.S | re.I)

# 読みを直したい言葉（自動の読みが違うもの。平塚の地名など）
FIX = {
    "市議会": "しぎかい", "元島": "もとしま", "平塚": "ひらつか", "日本": "にほん",
    "真土": "しんど", "大神": "おおかみ", "金目": "かなめ", "吉沢": "きさわ", "花水": "はなみず",
    "崇善": "すうぜん", "南原": "みなみはら", "公所": "ぐぞ", "纒": "まとい", "河内": "こうち",
    "達上ケ丘": "たつかみがおか", "夕陽ケ丘": "ゆうひがおか", "龍城ケ丘": "りゅうじょうがおか",
    "黒部丘": "くろべがおか", "浅間町": "せんげんちょう", "見附町": "みつけちょう", "札場町": "ふだばちょう",
    "宮松町": "みやまつちょう", "紅谷町": "べにやちょう", "明石町": "あかしちょう", "八重咲町": "やえざきちょう",
    "錦町": "にしきちょう", "代官町": "だいかんちょう", "宝町": "たからちょう", "松風町": "まつかぜちょう",
    "桃浜町": "ももはまちょう", "老松町": "おいまつちょう", "豊原町": "とよはらちょう", "千石河岸": "せんごくがし",
    "天沼": "あまぬま", "東八幡": "ひがしやわた", "西八幡": "にしやわた", "八幡山": "はちまんやま",
    "久領堤": "くりょうづつみ", "撫子原": "なでしこはら", "菫平": "すみれだいら", "根坂間": "ねざかま",
    "出縄": "いでなわ", "小鍋島": "こなべしま",
}
_FIXRE = re.compile("(" + "|".join(sorted(map(re.escape, FIX), key=len, reverse=True)) + ")")


def _hira(s: str) -> str:
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def _kana(c: str) -> bool:
    return "ぁ" <= c <= "ゖ" or "ァ" <= c <= "ヶ" or c == "ー"


def _ruby(surface: str, reading: str) -> str:
    s, r = surface, _hira(reading)
    pre = suf = ""
    while s and r and _kana(s[-1]) and _hira(s[-1]) == r[-1]:
        suf = s[-1] + suf
        s, r = s[:-1], r[:-1]
    while s and r and _kana(s[0]) and _hira(s[0]) == r[0]:
        pre += s[0]
        s, r = s[1:], r[1:]
    if not s or not r or s == r:
        return surface
    return f'{pre}<ruby>{s}<rt data-r="{r}"></rt></ruby>{suf}'


def _tok(t: str) -> str:
    out = []
    ws = list(_TAGGER(t))
    for i, w in enumerate(ws):
        sf = w.surface
        sp = getattr(w, "white_space", "") or ""
        if not KANJI.search(sf):
            out.append(sp + sf)
            continue
        kana = getattr(w.feature, "kana", None)
        if sf == "何" and i + 1 < len(ws) and ws[i + 1].surface[:1] in "がをもでかのに":
            kana = "ナニ"
        out.append(sp + (_ruby(sf, kana) if kana and kana != "*" else sf))
    return "".join(out)


@lru_cache(maxsize=200000)
def _text(t: str) -> str:
    if not KANJI.search(t):
        return t
    out = []
    for i, seg in enumerate(_FIXRE.split(t)):
        if i % 2:
            out.append(f'<ruby>{seg}<rt data-r="{FIX[seg]}"></rt></ruby>')
        elif seg:
            out.append(_tok(seg) if KANJI.search(seg) else seg)
    return "".join(out)


def add(html: str) -> str:
    """HTMLの文字の部分だけに、ふりがなを付ける（タグ・スクリプトはそのまま）。"""
    if _TAGGER is None:
        return html
    parts = SPLIT.split(html)
    out = []
    in_ruby = 0
    for p in parts:
        if not p:
            continue
        if p.startswith("<"):
            low = p[:6].lower()
            if low.startswith("<ruby"):
                in_ruby += 1
            elif low.startswith("</ruby"):
                in_ruby -= 1
            out.append(p)
        elif in_ruby:
            out.append(p)
        else:
            out.append(_text(p))
    return "".join(out)
