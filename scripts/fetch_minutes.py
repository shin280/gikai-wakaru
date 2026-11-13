"""会議録検索システム（dbsr.jp）から、各定例会の本会議の会議録（本文）を取って保存する。

討論（各会派が賛成・反対の理由を述べる場面）は、最終日の本文にある。
取った本文は data/raw/minutes/<定例会>/ に保存し、parse_minutes.py で読む。
"""
import calendar
import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "minutes"
BASE = "https://www.city.hiratsuka.kanagawa.dbsr.jp/"
UA = "gikai-wakaru (+https://github.com/shin280/gikai-wakaru)"
S = requests.Session()
S.headers["User-Agent"] = UA


def get(url: str) -> str:
    for _ in range(3):
        r = S.get(url, timeout=60)
        if r.status_code == 429:
            time.sleep(int(r.headers.get("Retry-After") or 60))
            continue
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        time.sleep(3)  # 相手のサーバーに負担をかけない
        return r.text
    raise RuntimeError(f"429が続きました: {url}")


def nz(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s)).strip()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    get(BASE)  # 最初の1回は429になりやすいので、ここで待つ
    for sp in sorted((ROOT / "data" / "sessions").glob("*.json"), reverse=True):
        sess = json.loads(sp.read_text(encoding="utf-8"))
        key, y, m = sess["key"], sess["year"], sess["month"]
        d = OUT / key
        if (d / "index.json").exists():
            continue  # 取得済み
        reiwa = y - 2018
        start = f"{y if m > 1 else y - 1}-{(m - 1) or 12:02d}-01"
        end = f"{y}-{m:02d}-{calendar.monthrange(y, m)[1]}"
        url = f"{BASE}100000?Template=list&QueryType=new&CabinetName=hon&TermStart={start}&TermEnd={end}"
        docs, page = [], 0
        while url and page < 5:
            soup = BeautifulSoup(get(url), "html.parser")
            for a in soup.find_all("a", href=True):
                t = nz(a.get_text(" "))
                if "Template=document" in a["href"] and f"令和{reiwa}年{m}月定例会" in t and "本文" in t:
                    docs.append({"title": t, "url": urljoin(BASE, a["href"].split("#")[0])})
            nxt = soup.find("a", string=re.compile("次"))
            url = urljoin(BASE, nxt["href"]) if nxt and nxt.get("href") else None
            page += 1
        if not docs:
            print(f"{key}: 会議録がまだありません")
            continue
        d.mkdir(parents=True, exist_ok=True)
        # 最終日（第○日の数字が一番大きい日）の本文だけを取る
        def day(doc):
            mm = re.search(r"第(\d+)日", doc["title"])
            return int(mm.group(1)) if mm else 0
        last = max(docs, key=day)
        html = get(last["url"])
        (d / "last_day.html").write_text(html, encoding="utf-8")
        (d / "index.json").write_text(json.dumps({"last_day": last, "docs": docs}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{key}: {last['title']} を保存")
    return 0


if __name__ == "__main__":
    sys.exit(main())
