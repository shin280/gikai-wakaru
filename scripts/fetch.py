"""平塚市議会の「議案名と議案概要・議決結果」ページを読み、定例会ごとの一覧をJSONで保存する。

市のページは定例会ごとに上書きされるので、取れた内容を data/sessions/ に残していく。
"""
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
JST = timezone(timedelta(hours=9))

RESULTS_URL = "https://www.city.hiratsuka.kanagawa.jp/gikai/page-c_02221.html"
BILLS_URL = "https://www.city.hiratsuka.kanagawa.jp/keikaku/page-c_02457.html"
UA = "gikai-wakaru (+https://github.com/shin280/gikai-wakaru)"

# 種別と番号: 議案第58号 / 認第1号 / 報告第9号 / 請願第4号ー1 / 会議案第3号
ITEM_RE = re.compile(r"(議案|会議案|認|報告|請願|陳情)第\s*([0-9０-９]+)\s*号(?:\s*[ー－\-]\s*([0-9０-９]+))?")
RESULTS = ["原案可決", "修正可決", "可決", "否決", "同意", "不同意", "承認", "不承認", "認定", "不認定",
           "趣旨採択", "不採択", "採択", "継続審査", "審議未了", "撤回"]
RESULT_RE = re.compile("(" + "|".join(RESULTS) + ")")
SESSION_RE = re.compile(r"(令和\s*([0-9０-９元]+)\s*年)?\s*([0-9０-９]+)\s*月\s*(定例会|臨時会)")


def nz(s: str) -> str:
    return unicodedata.normalize("NFKC", s).strip()


def get(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def reiwa_to_year(s: str | None) -> int | None:
    if not s:
        return None
    s = nz(s)
    return 2018 + (1 if s == "元" else int(s))


def parse_results(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find(id="main") or soup.find("main") or soup.body or soup

    # 見出しから定例会名を取る
    session_name, month, kind, year = None, None, None, None
    for h in main.find_all(["h1", "h2", "h3"]):
        m = SESSION_RE.search(nz(h.get_text()))
        if m:
            session_name = nz(m.group(0))
            year = reiwa_to_year(m.group(2))
            month = int(nz(m.group(3)))
            kind = m.group(4)
            break

    # 本文を行に分け、「番号・結果・件名」を拾う。表でも段落でも動くように、テキストの並びで読む。
    lines = [nz(t) for t in main.get_text("\n").split("\n")]
    lines = [l for l in lines if l]
    items, seen = [], set()
    for i, line in enumerate(lines):
        for m in ITEM_RE.finditer(line):
            kind_ = m.group(1)
            num = int(nz(m.group(2)))
            sub = int(nz(m.group(3))) if m.group(3) else None
            key = f"{kind_}{num}" + (f"-{sub}" if sub else "")
            if key in seen:
                continue
            # 同じ行の残りと次の数行から、結果と件名を探す
            window = [line[m.end():]] + lines[i + 1:i + 4]
            result, title = None, None
            for w in window:
                if ITEM_RE.search(w) and w is not window[0]:
                    break  # 次の案件に入った
                rm = RESULT_RE.search(w)
                if rm and not result:
                    result = rm.group(1)
                    w = (w[:rm.start()] + w[rm.end():]).strip()
                w = w.strip(" 　:：|")
                if w and not title and not RESULT_RE.fullmatch(w):
                    title = w
            if not title:
                continue
            title = re.sub(r"[（(](以上\d+案件.*?|提案説明.*?)[)）]$", "", title).strip()
            seen.add(key)
            items.append({
                "id": key, "kind": kind_, "number": num, "sub": sub,
                "label": f"{kind_}第{num}号" + (f"ー{sub}" if sub else ""),
                "title": title.strip('"“”'),
                "result": result,
            })

    if not year:
        # 見出しに年がなければ、件名の「令和8年度」などの最大値から推定（3月議会は翌年度予算が出るため最大値で合う）
        years = [reiwa_to_year(y) for it in items for y in re.findall(r"令和\s*([0-9元]+)\s*年度", it["title"])]
        year = max(years) if years else None
    return {"session_name": session_name, "year": year, "month": month, "kind": kind, "items": items}


def parse_bill_pdfs(html: str) -> list[dict]:
    """提出議案ページから、定例会ごとのPDFリンクを拾う。"""
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find(id="main") or soup.find("main") or soup.body or soup
    out, current = [], None
    for el in main.find_all(["h2", "h3", "a"]):
        if el.name in ("h2", "h3"):
            current = nz(el.get_text())
        elif el.get("href", "").lower().endswith(".pdf") and current:
            href = requests.compat.urljoin(BILLS_URL, el["href"])
            out.append({"session": current, "title": nz(el.get_text()), "url": href})
    return out


def main() -> int:
    now = datetime.now(JST)
    raw = DATA / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    html = get(RESULTS_URL)
    (raw / "results_latest.html").write_text(html, encoding="utf-8")
    parsed = parse_results(html)
    if not parsed["items"] or not parsed["year"] or not parsed["month"]:
        print("議決結果ページを読み取れませんでした。ページの形が変わった可能性があります。", file=sys.stderr)
        print(json.dumps({k: parsed[k] for k in ("session_name", "year", "month")}, ensure_ascii=False), file=sys.stderr)
        return 1

    try:
        pdfs = parse_bill_pdfs(get(BILLS_URL))
    except Exception as e:  # 議案書PDFの一覧が取れなくても一覧の更新は続ける
        print(f"提出議案ページの取得に失敗: {e}", file=sys.stderr)
        pdfs = []

    key = f"{parsed['year']}-{parsed['month']:02d}" + ("" if parsed["kind"] == "定例会" else "-rinji")
    path = DATA / "sessions" / f"{key}.json"
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    session_label = f"{parsed['month']}月{parsed['kind']}"
    reiwa = parsed["year"] - 2018
    record = {
        "key": key,
        "name": f"令和{reiwa}年{session_label}",
        "year": parsed["year"],
        "month": parsed["month"],
        "source": RESULTS_URL,
        "pdfs": [p for p in pdfs if f"令和{reiwa}年{parsed['month']}月" in p["session"]] or old.get("pdfs", []),
        "items": parsed["items"],
        "first_seen": old.get("first_seen", now.isoformat(timespec="seconds")),
    }
    # 中身が変わったときだけ更新日時を変える
    if {k: v for k, v in old.items() if k != "updated"} != record:
        record["updated"] = now.isoformat(timespec="seconds")
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"更新: {path.name}（{len(record['items'])}件）")
    else:
        print(f"変化なし: {path.name}")

    # 60日ルール対策: 毎回、最終確認日時を書き込む
    (DATA / "last_checked.txt").write_text(now.isoformat(timespec="seconds") + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
