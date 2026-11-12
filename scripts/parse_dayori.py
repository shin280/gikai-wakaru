"""議会だよりの審議結果の表（data/raw/dayori/）から、会派ごとの賛否を data/votes/ に保存する。

市の議決結果ページは最新の定例会しか載らないので、議会だよりにある過去の定例会は
ここで data/sessions/ にも一覧を作る（すでにあれば触らない）。
"""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "dayori"
VOTES = ROOT / "data" / "votes"
SESS = ROOT / "data" / "sessions"
RESULTS = ("原案可決", "修正可決", "可決", "否決", "同意", "不同意", "承認", "不承認", "認定", "不認定",
           "趣旨採択", "不採択", "採択", "継続審査")
KIND_BY_HEADER = {"議案番号": "議案", "会議案番号": "会議案", "請願番号": "請願", "陳情番号": "陳情"}


def nz(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    return s.replace("О", "O").replace("〇", "○").strip()


def item_id(kind: str, cell: str) -> tuple[str, str, int, int | None] | None:
    c = nz(cell).replace(" ", "")
    m = re.match(r"(認|報告)?第(\d+)号(?:[-ー－](\d+))?$", c)
    if not m:
        return None
    k = m.group(1) or kind
    num, sub = int(m.group(2)), (int(m.group(3)) if m.group(3) else None)
    return k + str(num) + (f"-{sub}" if sub else ""), k, num, sub


def parse_vote(cell: str) -> dict:
    """'○' / '×' / '○6\n欠1' を {'賛成':6,'欠席':1} の形にする。数字がないものは会派全体。"""
    c = nz(cell).replace("\n", " ")
    names = {"○": "賛成", "×": "反対", "欠": "欠席", "退": "退席", "-": "なし", "－": "なし"}
    out = {}
    for sym, n in re.findall(r"([○×欠退\-－])\s*(\d*)", c):
        out[names[sym]] = int(n) if n else None
    return out


def legend(text: str) -> list[dict]:
    t = nz(text)
    out = []
    for abbr, name, count in re.findall(r"([清公湘し共AB自立維国])\s*(?:…|\.)+\s*([^\s（(]+)\s*[（(](\d+名|無所属)[)）]", t):
        if all(o["abbr"] != abbr for o in out):
            out.append({"abbr": abbr, "name": name,
                        "count": int(count[:-1]) if count.endswith("名") else 1,
                        "independent": count == "無所属"})
    return out


def session_key(title: str) -> tuple[str, str, int, int] | None:
    m = re.search(r"令和\s*(\d+)\s*年\s*(\d+)\s*月(定例会|臨時会)", nz(title))
    if not m:
        return None
    year, month = 2018 + int(m.group(1)), int(m.group(2))
    return f"{year}-{month:02d}", f"令和{m.group(1)}年{month}月{m.group(3)}", year, month


def main():
    VOTES.mkdir(parents=True, exist_ok=True)
    index = json.loads((RAW / "index.json").read_text(encoding="utf-8"))
    for iss in index:
        sk = session_key(iss["title"])
        if not sk:
            continue
        key, name, year, month = sk
        text = (RAW / f"{iss['no']}.txt").read_text(encoding="utf-8")
        tables = json.loads((RAW / f"{iss['no']}.tables.json").read_text(encoding="utf-8"))
        leg = legend(text)
        votes, items = {}, []
        for tb in tables:
            if not tb or not tb[0]:
                continue
            raw_head = [nz(h) for h in tb[0]]
            head = [re.sub(r"\s+", "", h) for h in raw_head]
            kind = KIND_BY_HEADER.get(head[0])
            if not kind:
                continue
            if any(re.search(r"\S\s+\S", h) for h in raw_head[3:]):
                print(f"第{iss['no']}号: 表の列がくずれているので賛否を読みません（{head}）")
                continue
            abbrs = [h for h in head[3:] if h]
            for row in tb[1:]:
                got = item_id(kind, row[0] or "")
                if not got:
                    continue
                iid, k, num, sub = got
                title = re.sub(r"\s*\n\s*", "", nz(row[1] or ""))
                res = next((r for r in RESULTS if nz(row[2] or "") == r), None) if kind != "請願" else \
                    next((r for r in RESULTS if r in nz(row[-1] or "")), None)
                items.append({"id": iid, "kind": k, "number": num, "sub": sub,
                              "label": f"{k}第{num}号" + (f"ー{sub}" if sub else ""), "title": title, "result": res})
                if abbrs and kind != "請願":
                    votes[iid] = {a: parse_vote(row[3 + i] or "") for i, a in enumerate(abbrs) if 3 + i < len(row)}
        if not votes:
            continue
        rec = {"key": key, "source": {"title": iss["title"], "page": iss["page"], "pdf": iss["pdf"]},
               "groups": leg, "votes": votes}
        (VOTES / f"{key}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        sp = SESS / f"{key}.json"
        if not sp.exists():
            sp.write_text(json.dumps({"key": key, "name": name, "year": year, "month": month,
                                      "source": iss["page"], "pdfs": [], "items": items}, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
            print(f"定例会の一覧を議会だよりから作成: {key}（{len(items)}件）")
        print(f"賛否: {key} {len(votes)}件、会派{len(leg)}")


if __name__ == "__main__":
    main()
