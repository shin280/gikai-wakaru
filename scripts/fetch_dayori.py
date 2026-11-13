"""「ひらつか議会だより」の一覧から各号を開き、「議案等の審議結果」の面（8面）のPDFを取ってテキストにする。

議会だよりの審議結果の表には、会派ごと（無所属は議員ごと）の賛否が載っている。
取ったPDFとテキストは data/raw/dayori/ に保存し、parse_dayori.py で読む。
"""
import json
import re
import sys
from pathlib import Path

import pdfplumber
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "dayori"
LIST_URL = "https://www.city.hiratsuka.kanagawa.jp/gikai/page-c_02220.html"
UA = "gikai-wakaru (+https://github.com/shin280/gikai-wakaru)"
MAX_ISSUES = 16  # 新しい号から何号分を見るか（約4年分）


def get(url: str) -> requests.Response:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    return r


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    soup = BeautifulSoup(get(LIST_URL).content, "html.parser")
    issues = []
    for a in soup.find_all("a", href=True):
        t = a.get_text(" ", strip=True)
        m = re.search(r"第\s*(\d+)\s*号", t)
        if m and "定例会" in t:
            url = requests.compat.urljoin(LIST_URL, a["href"])
            if all(i["url"] != url for i in issues):
                issues.append({"no": int(m.group(1)), "label": t, "url": url})
    issues.sort(key=lambda i: i["no"], reverse=True)
    print("見つけた号:", [i["no"] for i in issues[:MAX_ISSUES]])

    index = []
    for iss in issues[:MAX_ISSUES]:
        page = BeautifulSoup(get(iss["url"]).content, "html.parser")
        title = page.find("h1").get_text(strip=True) if page.find("h1") else iss["label"]
        pdf = None
        for a in page.find_all("a", href=True):
            t = a.get_text(" ", strip=True)
            if a["href"].lower().endswith(".pdf") and "審議結果" in t:
                pdf = requests.compat.urljoin(iss["url"], a["href"])
                break
        if not pdf:
            print(f"第{iss['no']}号: 審議結果のPDFが見つかりません", file=sys.stderr)
            continue
        dest = OUT / f"{iss['no']}.pdf"
        if not dest.exists():
            dest.write_bytes(get(pdf).content)
        with pdfplumber.open(dest) as doc:
            text = "\n\n".join((p.extract_text(layout=True) or "") for p in doc.pages)
            tables = [t for p in doc.pages for t in p.extract_tables()]
        (OUT / f"{iss['no']}.txt").write_text(text, encoding="utf-8")
        (OUT / f"{iss['no']}.tables.json").write_text(json.dumps(tables, ensure_ascii=False, indent=1), encoding="utf-8")
        index.append({"no": iss["no"], "title": title, "page": iss["url"], "pdf": pdf})
        print(f"第{iss['no']}号: {title} → {len(text)}文字、表{len(tables)}個")
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
