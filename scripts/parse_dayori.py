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
    """「清……清風クラブ（８名）」「Ａ……佐藤由美子（無所属）」の凡例を読む。名前の中の空白は詰める。"""
    t = nz(text)
    out = []
    pat = r"(\S)\s*(?:…|\.){2,}\s*([^（(\n]+?)\s*[（(]\s*(?:(\d+)\s*名|(無所属))\s*[)）]"
    for abbr, name, count, indep in re.findall(pat, t):
        name = re.sub(r"\s+", "", name)
        if all(o["abbr"] != abbr for o in out):
            out.append({"abbr": abbr, "name": name, "count": int(count) if count else 1, "independent": bool(indep)})
    return out


SYM = r"[○〇×欠退][0-9０-９]*"
ROW_RE = re.compile(r"第\s*([0-9０-９]+)\s*号(?:\s*[ー－-]\s*([0-9０-９]+))?\s*(.*?)\s*(" + "|".join(RESULTS) + r")((?:\s+" + SYM + r")*)")
TITLE_END = ("条例", "〕", "について", "予算", "意見書", "請願", "決議", "決算")


def parse_text(text: str, abbrs: list[str]) -> tuple[list[dict], dict]:
    """表がくずれた号のために、レイアウトを保ったテキストから行を読む。

    左の列（市長提出議案）と右の列（会議案・請願・報告）を、行の中の位置で分ける。
    件名が複数行にわたるときは、前後の行をつなぐ。件名の終わり方（条例、〕など）で区切る。
    """
    lines = text.split("\n")  # 列の位置を保つため、ここでは正規化しない
    split = 50  # 件名の左の列はここまで
    right = 45  # 番号がここより右にあれば右の列
    items, votes = [], {}
    left_rows = []  # (行番号, 番号, 件名, 結果, 賛否)
    for i, l in enumerate(lines):
        for m in ROW_RE.finditer(l):
            syms = re.findall(SYM, m.group(5))
            num = int(nz(m.group(1)))
            if m.start() < right and len(syms) == len(abbrs):
                left_rows.append([i, num, nz(m.group(3)), m.group(4), syms])
            elif m.start() >= right and len(syms) == len(abbrs):
                iid = f"会議案{num}"
                items.append({"id": iid, "kind": "会議案", "number": num, "sub": None,
                              "label": f"会議案第{num}号", "title": nz(m.group(3)), "result": m.group(4)})
                votes[iid] = {a: parse_vote(x) for a, x in zip(abbrs, syms)}
    # 左の列の件名を前後の行から組み立てる
    def frag(i):
        part = nz(lines[i][:split]) if i < len(lines) else ""
        if not part or re.match(r"第\s*\d+\s*号", part) or re.search(r"番号|件 名|結果|議案$", part):
            return ""
        return part
    for k, (i, num, title, res, syms) in enumerate(left_rows):
        if not title:
            before, j = [], i - 1
            while j >= 0 and frag(j) and not frag(j).endswith(TITLE_END) and (k == 0 or j > left_rows[k - 1][0]):
                before.insert(0, frag(j)); j -= 1
            after, j = [], i + 1
            if not (before and "".join(before).endswith(TITLE_END)):
                while j < len(lines) and frag(j) and (k + 1 == len(left_rows) or j < left_rows[k + 1][0]):
                    after.append(frag(j)); j += 1
                    if after[-1].endswith(TITLE_END):
                        break
            title = "".join(before + after)
        iid = f"議案{num}"
        items.insert(0 if not items else len([x for x in items if x["kind"] == "議案"]),
                     {"id": iid, "kind": "議案", "number": num, "sub": None, "label": f"議案第{num}号",
                      "title": title, "result": res})
        votes[iid] = {a: parse_vote(x) for a, x in zip(abbrs, syms)}
    return items, votes


def abbrs_from_text(text: str) -> list[str]:
    """「件 名  結果  清 公 湘 …」の見出し行から会派の略称を並び順どおりに取る。"""
    for l in text.split("\n"):
        n = nz(l)
        m = re.search(r"結果((?:\s+\S)+)", n)
        if m:
            toks = m.group(1).split()
            if len(toks) >= 5 and all(len(t) == 1 for t in toks):
                return toks
    return []


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
        votes, items, broken, abbrs_seen = {}, [], False, []
        for tb in tables:
            if not tb or not tb[0]:
                continue
            raw_head = [nz(h) for h in tb[0]]
            head = [re.sub(r"\s+", "", h) for h in raw_head]
            if "結果" in head and len([h for h in head if len(h) == 1]) >= 5 and not abbrs_seen:
                abbrs_seen = [h for h in head[head.index("結果") + 1:] if h]
            if head and head[0] == "件名":
                broken = True  # 番号の列が切れている
            kind = KIND_BY_HEADER.get(head[0])
            if not kind:
                continue
            if any(re.search(r"\S\s+\S", h) for h in raw_head[3:]):
                broken = True
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
        if not abbrs_seen:
            abbrs_seen = abbrs_from_text(text)
        if (broken or not votes) and abbrs_seen:
            t_items, t_votes = parse_text(text, abbrs_seen)
            if t_items and len([i for i in t_items if i["kind"] == "議案"]) >= len([i for i in items if i["kind"] == "議案"]):
                print(f"第{iss['no']}号: 表がくずれていたので、テキストから{len(t_items)}件を読みました")
                petitions = [i for i in items if i["kind"] == "請願"]
                # 請願は表から（件名が「請願」で終わる行）。賛否は載っていない
                for tb in tables:
                    for row in tb[1:]:
                        if row and len(row) >= 3 and nz(row[1] or "").replace("\n", "").endswith("請願"):
                            got = item_id("請願", row[0] or "")
                            if got and all(p["id"] != got[0] for p in petitions):
                                iid, k, num, sub = got
                                petitions.append({"id": iid, "kind": "請願", "number": num, "sub": sub,
                                                  "label": f"請願第{num}号", "title": re.sub(r"\s+", "", nz(row[1])),
                                                  "result": next((r for r in RESULTS if r in nz(row[-1] or "")), None)})
                # 会議案の件名は、くずれていない表のほうが完全なことがある
                for tb in tables:
                    if tb and re.sub(r"\s+", "", nz(tb[0][0] or "")) == "会議案番号":
                        for row in tb[1:]:
                            got = item_id("会議案", row[0] or "")
                            for it in t_items:
                                if got and it["id"] == got[0] and len(nz(row[1] or "")) > len(it["title"]):
                                    it["title"] = re.sub(r"\s+", "", nz(row[1]))
                items, votes = t_items + petitions, t_votes
        if not votes:
            continue
        abbr_set = {g["abbr"] for g in leg}
        gian = [i for i in items if i["kind"] == "議案"]
        ok = (len(leg) >= 5 and len(gian) >= 5 and all(i["title"] for i in gian)
              and all(set(v) == abbr_set for v in votes.values()))
        if not ok:
            print(f"第{iss['no']}号（{key}）: 読み取り結果が信頼できないので保存しません"
                  f"（凡例{len(leg)}・議案{len(gian)}件・会派の一致{all(set(v) == abbr_set for v in votes.values())}）")
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
