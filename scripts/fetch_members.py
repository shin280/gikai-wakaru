"""市議会の「会派・委員会の構成一覧」ページから、会派ごとの所属議員を data/members.json に保存する。"""
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
URL = "https://www.city.hiratsuka.kanagawa.jp/gikai/page-c_02300.html"
UA = "gikai-wakaru (+https://github.com/shin280/gikai-wakaru)"
GROUP_RE = re.compile(r"^(.+?)\s*[（(]\s*(\d+)\s*名\s*[)）]$")


def nz(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s)).strip()


def main() -> int:
    r = requests.get(URL, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    raw = ROOT / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "members_latest.html").write_bytes(r.content)
    soup = BeautifulSoup(r.content, "html.parser")
    main_el = soup.find(id="main") or soup.find("main") or soup.body
    updated = None
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", main_el.get_text())
    if m:
        updated = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    groups, cur = [], None
    table = main_el.find("table")  # 最初の表が「会派等一覧」
    for tr in table.find_all("tr") if table else []:
        cells = [nz(c.get_text(" ")) for c in tr.find_all(["th", "td"])]
        cells = [c for c in cells if c]
        if not cells:
            continue
        gm = GROUP_RE.match(cells[0])
        if gm:
            cur = {"name": gm.group(1).replace(" ", ""), "count": int(gm.group(2)), "members": []}
            groups.append(cur)
            cells = cells[1:]
        elif cells[0] == "無所属":
            cur = {"name": "無所属", "count": 1, "members": [], "independent": True}
            groups.append(cur)
            cells = cells[1:]
        if not cur or not cells:
            continue
        nm = re.match(r"^([^（(]+?)\s*[（(]([^)）]*)[)）]\s*(.*)$", cells[0])
        if not nm:
            continue
        roles = " ".join(x for x in [nm.group(3)] + cells[1:] if x)
        cur["members"].append({"name": nm.group(1).replace(" ", " "), "kana": nm.group(2), "roles": roles})
    groups = [g for g in groups if g["members"]]
    if not groups:
        print("会派の構成を読み取れませんでした。data/raw/members_latest.html を確認してください。", file=sys.stderr)
        return 1
    out = {"source": URL, "updated": updated, "groups": groups}
    (ROOT / "data" / "members.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("会派:", [(g["name"], len(g["members"])) for g in groups])
    return 0


if __name__ == "__main__":
    sys.exit(main())
