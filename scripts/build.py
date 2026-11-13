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
KIND_EN = {"議案": "Bills", "認": "Financial statements", "会議案": "Council proposals", "請願": "Petitions", "陳情": "Petitions", "報告": "Reports"}
GOOD = {"可決", "原案可決", "修正可決", "同意", "承認", "認定", "採択", "趣旨採択"}
BAD = {"否決", "不同意", "不承認", "不認定", "不採択"}

e = html.escape

CSS = """
:root{--red:#ff0033;--red-d:#c4002a;--redbg:#fff0f3;--ink:#16181d;--sub:#646a73;--line:#e7e9ee;--bg:#f4f5f7;--card:#fff;
--ok:#c4002a;--okbg:#fff0f3;--ng:#3a3f47;--ngbg:#eceef1;--warn:#7a5a00;--warnbg:#fff7e0}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Noto Sans JP",system-ui,sans-serif;line-height:1.8;font-size:16px;-webkit-font-smoothing:antialiased}
a{color:var(--red-d)}
.wrap{max-width:720px;margin:0 auto;padding:0 16px 56px}
header.site{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
header.site .wrap{padding-top:12px;padding-bottom:12px;display:flex;align-items:center;gap:8px}
.logo{font-weight:700;font-size:17px;text-decoration:none;color:var(--ink);display:flex;align-items:center;gap:8px}
.logo::before{content:"";width:22px;height:16px;border-radius:5px;background:var(--red);
-webkit-mask:none;box-shadow:inset 0 0 0 0 #fff}
.logo span{color:var(--red)}
.tagline{display:none}
h1{font-size:24px;line-height:1.5;margin:20px 0 10px;font-weight:700}
h2{font-size:18px;margin:0 0 12px;line-height:1.4;font-weight:700}
h2 small{display:none}
h3{font-size:16px;margin:16px 0 4px}
section{background:var(--card);border-radius:16px;padding:20px 20px 12px;margin-top:14px;box-shadow:0 1px 2px rgba(16,24,40,.04),0 1px 8px rgba(16,24,40,.04)}
p{margin:0 0 10px}ul{margin:0 0 10px;padding-left:1.2em}li{margin-bottom:6px}
.muted{color:var(--sub);font-size:13px}
.item{display:flex;gap:12px;align-items:flex-start;padding:12px 0;border-top:1px solid var(--line)}.item:first-of-type{border-top:0;padding-top:2px}
.badge{flex:none;font-size:12px;font-weight:700;padding:2px 10px;border-radius:6px;background:var(--okbg);color:var(--ok);margin-top:3px;white-space:nowrap}
.badge.ng{background:var(--ngbg);color:var(--ng)}.badge.none{background:#eef0f3;color:var(--sub)}
.item .no{font-size:12px;color:var(--sub);display:block}.item .t{display:block;font-weight:500}
.item a.t{text-decoration:none;color:var(--ink)}.item a.t::after{content:" →";color:var(--red)}
.ai{background:var(--warnbg);color:var(--warn);border-radius:12px;padding:10px 14px;font-size:13px;margin-top:14px}
.toggle{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:99px;padding:3px;gap:2px;margin:12px 0 4px}
.toggle button{border:0;background:transparent;padding:7px 16px;border-radius:99px;font:inherit;font-size:13px;color:var(--sub);cursor:pointer}
.toggle button[aria-pressed=true]{background:var(--red);color:#fff;font-weight:700}
.detail{display:none}body.is-detail .detail{display:block}body.is-detail .easy{display:none}
.money{font-weight:700}.formal{font-size:13px;color:var(--sub);margin:0}
.meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:18px}
.tag{font-size:12px;padding:2px 10px;border-radius:99px;background:#fff;border:1px solid var(--line);color:var(--sub)}
.steps{display:flex;margin:4px 0 6px}
.step{flex:1;text-align:center;font-size:12px;color:var(--sub);position:relative;padding-top:24px}
.step::before{content:"";position:absolute;top:4px;left:50%;transform:translateX(-50%);width:16px;height:16px;border-radius:50%;background:#d6d9df;z-index:1}
.step::after{content:"";position:absolute;top:11px;left:50%;width:100%;height:2px;background:#d6d9df}
.step:last-child::after{display:none}
.step.done{color:var(--ink);font-weight:700}.step.done::before{background:var(--red)}.step.done::after{background:var(--red)}
details{border-top:1px solid var(--line);padding:10px 0}details:first-of-type{border-top:0}summary{cursor:pointer;font-weight:700}
footer{font-size:12px;color:var(--sub);margin-top:28px}
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
<header class="site"><div class="wrap"><a class="logo" href="{root}index.html">ひらつか議会 <span>わかる版</span></a><span class="tagline">HIRATSUKA CITY COUNCIL, MADE EASY</span></div></header>
<main class="wrap">{body}
<footer><p><b>運営：元島しん</b>（平塚市議会議員・しらさぎ・無所属クラブ所属）。会派ごとの賛否は、すべての会派を同じ形で、議会だよりの記載のとおりに載せています。<a href="{root}about.html">このサイトについて</a></p><p>このサイトは、平塚市が公開している資料をもとに、プログラムとAIが自動で作っています。人による確認はしていないため、間違いが含まれる可能性があります。大事な判断の前には、各ページの「元の資料」で必ず確かめてください。</p>
<p><a href="{report}">間違いを報告する</a> ・ <a href="https://github.com/{REPO}">このサイトのしくみ（GitHub）</a></p></footer>
</main>{TOGGLE_JS}</body></html>
"""


def h2(ja: str, en: str) -> str:
    return f"<h2>{e(ja)}<small>{e(en)}</small></h2>"


def badge(result: str | None) -> str:
    if not result:
        return '<span class="badge none">報告</span>'
    cls = "ng" if result in BAD else ""
    return f'<span class="badge {cls}">{e(result)}</span>'


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


MEMBERS = None


def vote_word(v: dict) -> str:
    if not v:
        return "記載なし"
    if len(v) == 1 and list(v.values())[0] is None:
        return list(v)[0]
    return "・".join(f"{k}{n if n is not None else ''}" for k, n in v.items())


def votes_for(session_key: str, item_id: str):
    vf = load_json(DATA / "votes" / f"{session_key}.json")
    if not vf or item_id not in vf["votes"]:
        return None, None
    return vf, vf["votes"][item_id]


def vote_summary(vf: dict, v: dict) -> str:
    """全会一致か、反対した会派はどこかを1行で。"""
    names = {g["abbr"]: g["name"] for g in vf["groups"]}
    against = [names.get(a, a) for a, x in v.items() if "反対" in x]
    if not against:
        return "全会一致"
    return "反対：" + "、".join(against)


def vote_headline(vf: dict, v: dict, result: str | None) -> str:
    sm = vote_summary(vf, v)
    if sm == "全会一致":
        return f"全会一致で{result or ''}"
    return f"賛成多数で{result}（{sm}）" if result in GOOD else f"{result or ''}（{sm}）"


def members_of(group: dict) -> list[str]:
    global MEMBERS
    if MEMBERS is None:
        MEMBERS = load_json(DATA / "members.json") or {"groups": []}
    if group.get("independent"):
        return [group["name"]]
    for g in MEMBERS["groups"]:
        if g["name"] == group["name"]:
            return [m["name"] for m in g["members"]]
    return []


def render_votes(s: dict, it: dict) -> str:
    vf, v = votes_for(s["key"], it["id"])
    if not v:
        return ""
    rows = ""
    for g in vf["groups"]:
        if g["abbr"] not in v:
            continue
        word = vote_word(v[g["abbr"]])
        cls = "ng" if "反対" in v[g["abbr"]] else ""
        mem = "、".join(members_of(g)) if not g.get("independent") else "無所属"
        label = f'{e(g["name"])}（{g["count"]}名）' if not g.get("independent") else e(g["name"])
        rows += f'<div class="item"><span class="badge {cls}">{e(word)}</span><div><span class="t">{label}</span><span class="no">{e(mem)}</span></div></div>'
    mu = (MEMBERS or {}).get("updated") or ""
    src = vf["source"]
    return f"""<section>{h2('会派ごとの賛否', 'Votes')}<p><b>{e(vote_headline(vf, v, it['result']))}</b></p>{rows}
<p class="muted">賛否は「{e(src['title'])}」の審議結果一覧によります。所属議員は市議会の会派構成のページ（{e(mu)}時点）によるもので、採決のときと違う場合があります。</p></section>"""


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
<div class="meta">{badge(it['result'])}<span class="tag">{e(s['name'])}</span><span class="tag">{e(KIND_LABEL.get(it['kind'], it['kind']))}</span></div>
<h1 class="easy">{e(sm['headline'])}</h1><h1 class="detail">{e(sm.get('headline_detail') or sm['headline'])}</h1>
<p class="formal">正式名称：{e(it['label'])} {e(it['title'])}</p>
<div class="toggle"><button type="button" id="b-easy" aria-pressed="true">やさしく</button><button type="button" id="b-detail" aria-pressed="false">詳しく</button></div>
<div class="ai">この説明はAIが市の資料から自動で作ったもので、人は確認していません。</div>
<section>{h2('審議のステータス','Status')}<div class="steps"><div class="step done">市が提出</div><div class="step done">委員会で審査</div><div class="step done">本会議で{e(it['result'] or '報告')}</div></div></section>
{render_votes(s, it)}
<section>{h2('何が決まったの？','What was decided')}{pts}</section>
{f'<section>{h2('数字で見ると','In numbers')}{calc}</section>' if calc else ''}
{f'<section>{h2('なぜ必要なの？（市の説明）','Why')}{why}</section>' if why else ''}
{f'<section>{h2('だれに関係する？','Who is affected')}<ul>{who}</ul></section>' if who else ''}
{f'<section>{h2('よくある質問','FAQ')}{faq}</section>' if faq else ''}
{f'<section>{h2('資料からは分からないこと','Not in the documents')}<ul>{unk}</ul></section>' if unk else ''}
<section>{h2('元の資料','Sources')}<ul>{src}<li><a href="{e(s['source'])}">平塚市議会 議決結果のページ</a></li></ul></section>
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
            vf, v = votes_for(s["key"], it["id"])
            vs = f'<span class="no">{e(vote_summary(vf, v))}</span>' if v else ""
            rows += f'<div class="item">{badge(it["result"])}<div><span class="no">{e(it["label"])}</span><span class="t">{t}</span>{vs}</div></div>'
        groups += f"<section>{h2(KIND_LABEL.get(kind, kind) + f'（{len(items)}件）', KIND_EN.get(kind, ''))}{rows}</section>"
    pdfs = "".join(f'<li><a href="{e(p["url"])}">{e(p["title"])}</a></li>' for p in s.get("pdfs", []))
    vf = load_json(DATA / "votes" / f"{s['key']}.json")
    dayori = f'<li><a href="{e(vf["source"]["pdf"])}">{e(vf["source"]["title"])}（審議結果・会派ごとの賛否）</a></li>' if vf else ""
    body = f"""<h1>{e(s['name'])}で決まったこと</h1>
<p class="muted">全{len(s['items'])}件。リンクのあるものは、わかりやすい説明のページがあります。</p>
{groups}
<section>{h2('元の資料','Sources')}<ul><li><a href="{e(s['source'])}">平塚市議会 議決結果のページ</a></li>{pdfs}{dayori}</ul></section>"""
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
{f'<section>{h2('最近決まったこと','Latest')}{latest}</section>' if latest else ''}
<section>{h2('定例会ごとの一覧','Sessions')}{rows or '<p>まだデータがありません。</p>'}</section>
<p class="muted">最終確認：{e(last_checked)}</p>"""
    return page("平塚市議会で決まったことを、わかりやすく", body)


def render_about() -> str:
    body = f"""<h1>このサイトについて</h1>
<section>{h2('運営者', 'Operator')}
<p>平塚市議会議員の元島しん（平塚ユーチューバーしん）が運営しています。所属会派はしらさぎ・無所属クラブです。</p>
<p>運営者は採決に加わる議員の一人です。そのため、次のことを決まりにしています。</p>
<ul><li>会派ごとの賛否は、ひらつか議会だよりの審議結果一覧の記載のとおりに、すべての会派を同じ形で載せる</li>
<li>賛否についての評価（良い・悪い）は書かない</li>
<li>反対・賛成の理由は、会議録にある各会派の討論から、出典付きで載せる</li></ul></section>
<section>{h2('しくみ', 'How it works')}
<p>毎朝、プログラムが平塚市議会の議決結果のページ、ひらつか議会だより、会派構成のページ、会議録を読みに行き、新しい内容があればこのサイトを作り直します。議案のわかりやすい説明はAIが市の資料から書いています。人による確認はしていないため、間違いが含まれる可能性があります。</p>
<p>説明を書くときの決まりと、プログラムはすべて公開しています。<a href="https://github.com/{REPO}">GitHub</a></p></section>
<section>{h2('間違いを見つけたら', 'Report')}
<p><a href="https://github.com/{REPO}/issues/new">こちらから報告</a>してください。</p></section>"""
    return page("このサイトについて", body)


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
    (OUT / "about.html").write_text(render_about(), encoding="utf-8")
    (OUT / "CNAME").write_text(DOMAIN + "\n")
    (OUT / ".nojekyll").write_text("")
    print(f"サイトを作成: 定例会{len(sessions)}件")


if __name__ == "__main__":
    main()
