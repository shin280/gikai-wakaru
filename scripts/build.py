"""data/ のJSONから静的サイトを site/ に作る。"""
import html
import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "site"
DOMAIN = "gikai.tubehira.jp"
REPO = "shin280/gikai-wakaru"
SITE_NAME = "ひらつか議会 わかる版"

KIND_ORDER = ["議案", "認", "会議案", "請願", "陳情", "報告"]
KIND_LABEL = {"議案": "議案", "認": "決算の認定", "会議案": "議員が出した議案・意見書", "請願": "請願",
              "陳情": "陳情", "報告": "市からの報告"}
GOOD = {"可決", "原案可決", "修正可決", "同意", "承認", "認定", "採択", "趣旨採択"}
BAD = {"否決", "不同意", "不承認", "不認定", "不採択"}

e = html.escape

CSS = """
:root{--ink:#1d2328;--sub:#5b6670;--line:#dfe3e6;--bg:#f6f7f5;--card:#fff;--accent:#0f6b5c;--soft:#e3f1ee;--warn:#8a5a00;--warnbg:#fff4dc;--ng:#9b2c2c;--ngbg:#fbeaea}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:"Noto Sans JP",system-ui,sans-serif;line-height:1.75;font-size:16px}
a{color:var(--accent)}.wrap{max-width:720px;margin:0 auto;padding:0 16px 48px}
header.site{background:#fff;border-bottom:1px solid var(--line)}header.site .wrap{padding-top:10px;padding-bottom:10px}
.logo{font-weight:700;font-size:15px;text-decoration:none;color:var(--ink)}.logo span{color:var(--accent)}
h1{font-size:23px;line-height:1.5;margin:18px 0 8px}h2{font-size:17px;margin:0 0 10px;padding-left:10px;border-left:4px solid var(--accent);line-height:1.4}h3{font-size:15px;margin:14px 0 4px}
section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px 12px;margin-top:14px}
p{margin:0 0 10px}ul{margin:0 0 10px;padding-left:1.2em}li{margin-bottom:4px}.muted{color:var(--sub);font-size:13px}
.item{display:flex;gap:10px;align-items:flex-start;padding:10px 0;border-top:1px solid var(--line)}.item:first-of-type{border-top:0}
.badge{flex:none;font-size:12px;font-weight:700;padding:1px 9px;border-radius:99px;background:var(--soft);color:var(--accent);margin-top:3px;white-space:nowrap}
.badge.ng{background:var(--ngbg);color:var(--ng)}.badge.none{background:#eceeed;color:var(--sub)}
.item .no{font-size:12px;color:var(--sub);display:block}.item .t{display:block}
.ai{background:var(--warnbg);border:1px solid #f0d9a8;color:var(--warn);border-radius:10px;padding:8px 12px;font-size:13px;margin-top:12px}
.toggle{display:flex;background:#e9ecea;border-radius:10px;padding:4px;gap:4px;margin:10px 0 4px}
.toggle button{flex:1;border:0;background:transparent;padding:8px;border-radius:7px;font:inherit;font-size:14px;color:var(--sub);cursor:pointer}
.toggle button[aria-pressed=true]{background:#fff;color:var(--ink);font-weight:700}
.detail{display:none}body.is-detail .detail{display:block}body.is-detail .easy{display:none}
.money{font-weight:700}.formal{font-size:13px;color:var(--sub)}
details{border-top:1px solid var(--line);padding:8px 0}details:first-of-type{border-top:0}summary{cursor:pointer;font-weight:500}
footer{font-size:12px;color:var(--sub);margin-top:22px}
"""

TOGGLE_JS = """<script>
(function(){var b=document.body,E=document.getElementById('b-easy'),D=document.getElementById('b-detail');if(!E)return;
function s(d){b.classList.toggle('is-detail',d);E.setAttribute('aria-pressed',!d);D.setAttribute('aria-pressed',d)}
E.onclick=function(){s(false)};D.onclick=function(){s(true)}})();
</script>"""


def page(title: str, body: str, depth: int = 0, desc: str = "") -> str:
    root = "../" * depth
    report = f"https://github.com/{REPO}/issues/new?title=" + e(f"間違いの報告：{title}")
    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}｜{SITE_NAME}</title><meta name="description" content="{e(desc or title)}">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<header class="site"><div class="wrap"><a class="logo" href="{root}index.html">ひらつか議会 <span>わかる版</span></a></div></header>
<main class="wrap">{body}
<footer><p>このサイトは、平塚市が公開している資料をもとに、プログラムとAIが自動で作っています。人による確認はしていないため、間違いが含まれる可能性があります。大事な判断の前には、各ページの「元の資料」で必ず確かめてください。</p>
<p><a href="{report}">間違いを報告する</a> ・ <a href="https://github.com/{REPO}">このサイトのしくみ（GitHub）</a></p></footer>
</main>{TOGGLE_JS}</body></html>
"""


def badge(result: str | None) -> str:
    if not result:
        return '<span class="badge none">報告</span>'
    cls = "ng" if result in BAD else ""
    return f'<span class="badge {cls}">{e(result)}</span>'


def load_sessions() -> list[dict]:
    ss = [json.loads(p.read_text(encoding="utf-8")) for p in (DATA / "sessions").glob("*.json")]
    return sorted(ss, key=lambda s: s["key"], reverse=True)


def summary_path(session_key: str, item_id: str) -> Path:
    return DATA / "summaries" / session_key / f"{item_id}.json"


def bill_slug(item_id: str) -> str:
    # 議案82 -> gian-82 のようにURLを英数字にする
    m = {"議案": "gian", "会議案": "kaigian", "認": "nin", "報告": "hokoku", "請願": "seigan", "陳情": "chinjo"}
    for k in sorted(m, key=len, reverse=True):
        if item_id.startswith(k):
            return m[k] + "-" + item_id[len(k):]
    return item_id


def render_bill(s: dict, it: dict, sm: dict) -> str:
    pts = ""
    for i, p in enumerate(sm.get("points", []), 1):
        amt = f'<p>予算：<span class="money">{e(p["amount"])}</span></p>' if p.get("amount") else ""
        det = f'<p class="detail">{e(p["detail"])}</p>' if p.get("detail") else ""
        pts += f'<h3>{i}. {e(p["title"])}</h3><p class="easy">{e(p["easy"])}</p>{det}{amt}'
    calc = "".join(f"<p>{e(x)}</p>" for x in sm.get("numbers", []))
    why = "".join(f"<p>{e(x)}</p>" for x in sm.get("why", []))
    who = "".join(f"<li><b>{e(w['name'])}</b>：{e(w['desc'])}</li>" for w in sm.get("who", []))
    faq = "".join(f"<details><summary>{e(q['q'])}</summary><p>{e(q['a'])}</p></details>" for q in sm.get("faq", []))
    unk = "".join(f"<li>{e(x)}</li>" for x in sm.get("unknowns", []))
    src = "".join(f'<li><a href="{e(x["url"])}">{e(x["title"])}</a></li>' for x in sm.get("sources", []))
    body = f"""
<p class="muted" style="margin-top:16px">{badge(it['result'])} {e(s['name'])}</p>
<h1 class="easy">{e(sm['headline'])}</h1><h1 class="detail">{e(sm.get('headline_detail') or sm['headline'])}</h1>
<p class="formal">正式名称：{e(it['label'])} {e(it['title'])}</p>
<div class="toggle"><button type="button" id="b-easy" aria-pressed="true">やさしく</button><button type="button" id="b-detail" aria-pressed="false">詳しく</button></div>
<div class="ai">この説明はAIが市の資料から自動で作ったもので、人は確認していません。</div>
<section><h2>何が決まったの？</h2>{pts}</section>
{f'<section><h2>数字で見ると</h2>{calc}</section>' if calc else ''}
{f'<section><h2>なぜ必要なの？（市の説明）</h2>{why}</section>' if why else ''}
{f'<section><h2>だれに関係する？</h2><ul>{who}</ul></section>' if who else ''}
{f'<section><h2>よくある質問</h2>{faq}</section>' if faq else ''}
{f'<section><h2>資料からは分からないこと</h2><ul>{unk}</ul></section>' if unk else ''}
<section><h2>元の資料</h2><ul>{src}<li><a href="{e(s['source'])}">平塚市議会 議決結果のページ</a></li></ul></section>
<p style="margin-top:14px"><a href="../s/{e(s['key'])}.html">← {e(s['name'])}の一覧に戻る</a></p>"""
    return page(sm["headline"], body, depth=1, desc=sm["headline"])


def render_session(s: dict) -> str:
    groups = ""
    for kind in KIND_ORDER:
        items = [i for i in s["items"] if i["kind"] == kind]
        if not items:
            continue
        rows = ""
        for it in items:
            sp = summary_path(s["key"], it["id"])
            if sp.exists():
                sm = json.loads(sp.read_text(encoding="utf-8"))
                t = f'<a href="../b/{s["key"]}-{bill_slug(it["id"])}.html">{e(sm["headline"])}</a>'
            else:
                t = e(it["title"])
            rows += f'<div class="item">{badge(it["result"])}<div><span class="no">{e(it["label"])}</span><span class="t">{t}</span></div></div>'
        groups += f"<section><h2>{e(KIND_LABEL.get(kind, kind))}（{len(items)}件）</h2>{rows}</section>"
    pdfs = "".join(f'<li><a href="{e(p["url"])}">{e(p["title"])}</a></li>' for p in s.get("pdfs", []))
    body = f"""<h1>{e(s['name'])}で決まったこと</h1>
<p class="muted">全{len(s['items'])}件。リンクのあるものは、わかりやすい説明のページがあります。</p>
{groups}
<section><h2>元の資料</h2><ul><li><a href="{e(s['source'])}">平塚市議会 議決結果のページ</a></li>{pdfs}</ul></section>"""
    return page(s["name"] + "で決まったこと", body, depth=1)


def render_index(sessions: list[dict], last_checked: str) -> str:
    rows = ""
    for s in sessions:
        n = sum(1 for i in s["items"] if summary_path(s["key"], i["id"]).exists())
        rows += f'<div class="item"><div><a href="s/{e(s["key"])}.html"><b>{e(s["name"])}</b></a><span class="no">全{len(s["items"])}件・説明ページ{n}件</span></div></div>'
    latest = ""
    if sessions:
        s = sessions[0]
        for it in s["items"]:
            sp = summary_path(s["key"], it["id"])
            if sp.exists():
                sm = json.loads(sp.read_text(encoding="utf-8"))
                latest += f'<div class="item">{badge(it["result"])}<div><span class="no">{e(it["label"])}</span><a class="t" href="b/{s["key"]}-{bill_slug(it["id"])}.html">{e(sm["headline"])}</a></div></div>'
    body = f"""<h1>平塚市議会で決まったことを、わかりやすく</h1>
<p>市議会で可決・否決されたことを、市の資料をもとに自動でまとめています。</p>
{f'<section><h2>最近決まったこと</h2>{latest}</section>' if latest else ''}
<section><h2>定例会ごとの一覧</h2>{rows or '<p>まだデータがありません。</p>'}</section>
<p class="muted">最終確認：{e(last_checked)}</p>"""
    return page("平塚市議会で決まったことを、わかりやすく", body)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "s").mkdir(parents=True)
    (OUT / "b").mkdir()
    sessions = load_sessions()
    lc = (DATA / "last_checked.txt")
    last = lc.read_text().strip() if lc.exists() else ""
    if last:
        last = datetime.fromisoformat(last).strftime("%Y年%-m月%-d日 %H:%M")
    for s in sessions:
        (OUT / "s" / f"{s['key']}.html").write_text(render_session(s), encoding="utf-8")
        for it in s["items"]:
            sp = summary_path(s["key"], it["id"])
            if sp.exists():
                sm = json.loads(sp.read_text(encoding="utf-8"))
                (OUT / "b" / f"{s['key']}-{bill_slug(it['id'])}.html").write_text(render_bill(s, it, sm), encoding="utf-8")
    (OUT / "index.html").write_text(render_index(sessions, last), encoding="utf-8")
    (OUT / "CNAME").write_text(DOMAIN + "\n")
    (OUT / ".nojekyll").write_text("")
    print(f"サイトを作成: 定例会{len(sessions)}件")


if __name__ == "__main__":
    main()
