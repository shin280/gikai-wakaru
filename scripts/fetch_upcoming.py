"""市長記者会見の「市議会定例会の提出案件」から、これから議会に出される議案を取る。

- 記者発表一覧（/press/index.html）で、タイトルに「市議会定例会の提出案件」を含む一番新しい記事を探す。
- 記事の中の「令和○年○月市議会定例会の提出案件」の見出しの下にある、議案ごとの小見出し（h5）と説明文を保存する。
- data/upcoming/<key>.json に保存する。やさしい説明（easy）がすでにあれば消さずに残す。
- 結果が出た定例会（data/sessions/<key>.json がある）は取らない。
"""
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "upcoming"
BASE = "https://www.city.hiratsuka.kanagawa.jp"
UA = {"User-Agent": "gikai-wakaru (+https://github.com/shin280/gikai-wakaru)"}


def get(url):
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    return BeautifulSoup(r.text, "html.parser")


def main():
    idx = get(BASE + "/press/index.html")
    link = None
    for a in idx.find_all("a"):
        if "市議会定例会の提出案件" in a.get_text():
            link = a
            break
    if not link:
        print("提出案件の記者発表が見つかりません")
        return
    url = requests.compat.urljoin(BASE + "/press/index.html", link["href"])
    parsed = parse(get(url))
    if not parsed:
        print("提出案件の見出しが見つかりません:", url)
        return
    key, m, items, kaiki = parsed
    if (ROOT / "data" / "sessions" / f"{key}.json").exists():
        print("結果が出ている定例会なので取らない:", key)
        return
    save(key, m, items, kaiki, url)


def parse(doc):
    h2 = None
    for h in doc.find_all("h2"):
        if re.search(r"令和(\d+)年(\d+)月市議会定例会の提出案件$", h.get_text(strip=True)):
            h2 = h
            break
    if not h2:
        return None
    m = re.search(r"令和(\d+)年(\d+)月", h2.get_text())
    key = f"{2018 + int(m.group(1))}-{int(m.group(2)):02d}"
    section = h2.find_parent(class_="m-mline") or h2.parent
    items = []
    for h in section.find_all(["h4", "h5"]):
        title = re.sub(r"\s+", " ", h.get_text(" ", strip=True))
        if re.match(r"^\d+\s*議案", title) or "単位" in title:
            continue
        texts, details = [], []
        for sib in h.next_siblings:
            if getattr(sib, "name", None) in ("h2", "h3", "h4", "h5", "table", "ol"):
                break
            t = sib.get_text(" ", strip=True) if hasattr(sib, "get_text") else str(sib).strip()
            if getattr(sib, "name", None) == "h6" and t:
                details.append(re.sub(r"\s+", " ", t))
            elif t:
                texts.append(t)
        ov = re.sub(r"\s+", " ", " ".join(texts)).replace("\xa0", " ").strip()
        cut = ov.find("ものです。")
        ov = ov[:cut + 5] if cut >= 0 else ov[:300]
        items.append({"title": title, "overview": ov, "details": details})
    extra = section.find("ol")
    if extra:
        for li in extra.find_all("li"):
            items.append({"title": li.get_text(strip=True), "overview": "追加で提出される予定の案件です。"})
    body = section.get_text(" ", strip=True)
    kaiki = re.search(r"会期は(?:令和\d+年)?(.{4,30}?)(?:です|となります)", body)
    return key, m, items, (kaiki.group(1) if kaiki else "")


def save(key, m, items, kaiki, url):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{key}.json"
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    easy = {i["title"]: i for i in old.get("items", []) if i.get("easy")}
    for it in items:
        if it["title"] in easy:
            it["easy"] = easy[it["title"]]["easy"]
    data = {**old, "key": key, "name": f"令和{m.group(1)}年{m.group(2)}月定例会", "press": url,
            "kaiki": kaiki or old.get("kaiki", ""), "items": items}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{key}: {len(items)}件を保存")


if __name__ == "__main__":
    main()
