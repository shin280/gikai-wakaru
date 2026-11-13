"""会議録検索システム（dbsr.jp）のページの形を調べるため、トップと数ページを保存する。調査用。"""
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "minutes_probe"
BASE = "https://www.city.hiratsuka.kanagawa.dbsr.jp/"
UA = "gikai-wakaru (+https://github.com/shin280/gikai-wakaru)"

OUT.mkdir(parents=True, exist_ok=True)
s = requests.Session()
s.headers["User-Agent"] = UA
seen = []
queue = [BASE]
while queue and len(seen) < 8:
    url = queue.pop(0)
    if url in seen:
        continue
    seen.append(url)
    import time
    r = s.get(url, timeout=60)
    if r.status_code == 429:
        print("429:", r.headers.get("Retry-After"), dict(r.headers))
        time.sleep(int(r.headers.get("Retry-After", "60") or 60))
        r = s.get(url, timeout=60)
        print("再試行:", r.status_code)
    time.sleep(3)
    r.encoding = r.apparent_encoding
    (OUT / f"{len(seen):02d}.html").write_text(f"<!-- {url} -->\n" + r.text, encoding="utf-8")
    for href in re.findall(r'href="([^"]+)"', r.text):
        u = urljoin(url, href.replace("&amp;", "&"))
        if "dbsr.jp" in u and any(k in u for k in ("Template=list", "Template=document", "Template=doc-all", "index.php")) and u not in seen:
            queue.append(u)
print("保存:", seen)
