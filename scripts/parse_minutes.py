"""会議録（最終日の本文）から討論を取り出し、議案ごとに data/minutes/<定例会>.json に保存する。

議長の「日程第○、議案第○号…を議題といたします」で、いま扱っている議案を知り、
「討論を行います」から採決までの「○番 ○○議員」の発言を討論として取る。
"""
import json
import re
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "minutes"
OUT = ROOT / "data" / "minutes"
NUM = r"[0-9０-９]+"


def nz(s):
    return unicodedata.normalize("NFKC", s)


def bill_ids(text: str) -> list[str]:
    """「議案第35号、第38号及び議案第42号」から 議案35, 議案38, 議案42 を取る。"""
    t = nz(text)
    out = []
    for m in re.finditer(r"(会議案|議案|請願|陳情|認)第(\d+)号((?:\s*(?:、|及び|並びに|,)\s*第\d+号)*)", t):
        kind = m.group(1)
        nums = [m.group(2)] + re.findall(r"第(\d+)号", m.group(3))
        out += [f"{kind}{int(n)}" for n in nums]
    return list(dict.fromkeys(out))


def stance_for(paragraphs: list[str], bid: str) -> str:
    kind, num = re.match(r"(\D+)(\d+)", bid).groups()
    if kind in ("請願", "陳情"):
        head = nz("".join(paragraphs[:2]))
        if "採択すべき" in head or "採択を求め" in head:
            return "採択を求める"
        if "不採択" in head and "賛成" in head:
            return "不採択に賛成"
    pat = re.compile(rf"{kind}?第{num}号")
    hits = [p for p in paragraphs if pat.search(nz(p))]
    for p in hits + paragraphs[:3]:
        q = nz(p)
        a, b = q.find("反対"), q.find("賛成")
        if a >= 0 and (b < 0 or a < b):
            return "反対"
        if b >= 0:
            return "賛成"
    return ""


def excerpt(paragraphs: list[str], bid: str, limit: int = 260) -> str:
    """その議案に触れた段落から、理由が書かれていそうな部分を抜き出す（会議録の文のまま）。"""
    kind, num = re.match(r"(\D+)(\d+)", bid).groups()
    pat = re.compile(rf"第{num}号")
    idx = next((i for i, p in enumerate(paragraphs) if pat.search(nz(p))), 0)
    # 「○○を代表し、～討論を行います」だけの段落は飛ばして、理由の段落から始める
    if re.search(r"討論(を行い|をし|をいた)", nz(paragraphs[idx])) and idx + 1 < len(paragraphs):
        idx += 1
    text = ""
    for p in paragraphs[idx: idx + 4]:
        text += p.strip()
        if len(text) >= limit:
            break
    return text[:limit] + ("…" if len(text) > limit else "")


def parse(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.get_text("\n")
    start = body.find("↓最初のヒットへ")
    body = body[start:] if start >= 0 else body
    # 「◯発言者　　本文」ごとに分ける
    speeches = re.split(r"\n\s*\d+:\s*\n", body)
    current, debating, out = [], False, []
    for sp in speeches:
        m = re.search(r"◯(.+?)　　+(.*)", sp, re.S)
        if not m:
            continue
        who, text = m.group(1), m.group(2)
        if "議長" in who:
            ids = bill_ids(text)
            if "議題" in text and ids:
                current = ids
            if "討論を行います" in text or "討論を行いますが" in text:
                debating = True
            elif "討論を終わります" in text or "採決を行います" in text or "これで討論を" in text:
                debating = False
            continue
        dm = re.match(rf"({NUM})番\s*(.+?)議員$", nz(who).strip())
        if debating and dm and current:
            name = dm.group(2).replace(" ", "")
            paras = [re.sub(r"\s+", "", p) for p in re.split(r"\n\s*\n", text) if p.strip()]
            mentioned = [b for b in bill_ids(text) if b in current] or current
            for b in mentioned:
                out.append({"bill": b, "speaker": name, "stance": stance_for(paras, b),
                            "intro": paras[0][:120], "excerpt": excerpt(paras, b)})
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for d in sorted(RAW.glob("*")):
        f = d / "last_day.html"
        if not f.exists():
            continue
        idx = json.loads((d / "index.json").read_text(encoding="utf-8"))
        debates = parse(f.read_text(encoding="utf-8"))
        rec = {"key": d.name, "source": idx["last_day"], "debates": debates}
        (OUT / f"{d.name}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{d.name}: 討論 {len(debates)}件（{len({x['speaker'] for x in debates})}人）")


if __name__ == "__main__":
    main()
