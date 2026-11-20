"""data/ のJSONから静的サイトを site/ に作る。"""
import html
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tags import tags_for  # noqa: E402
import ogp  # noqa: E402
import glossary  # noqa: E402
DATA = ROOT / "data"
OUT = ROOT / "site"
DOMAIN = "gikai.tubehira.jp"
# 独自ドメインがつながるまでは GitHub Pages のアドレス。つながったら https://gikai.tubehira.jp にする
SITE_URL = "https://gikai.tubehira.jp"
REPO = "shin280/gikai-wakaru"
SITE_NAME = "猫でもわかる平塚市議会"
OG_VER = "neko2"  # SNS用画像を変えたら上げる（XやLINEの古い画像のキャッシュを避けるため）

KIND_ORDER = ["議案", "認", "会議案", "請願", "陳情", "報告"]
KIND_LABEL = {"議案": "議案", "認": "決算の認定", "会議案": "議員が出した議案・意見書", "請願": "請願",
              "陳情": "陳情", "報告": "市からの報告"}
KIND_EN = {"議案": "Bills", "認": "Financial statements", "会議案": "Council proposals", "請願": "Petitions", "陳情": "Petitions", "報告": "Reports"}
GOOD = {"可決", "原案可決", "修正可決", "同意", "承認", "認定", "採択", "趣旨採択"}
BAD = {"否決", "不同意", "不承認", "不認定", "不採択"}

e = html.escape

CSS = """
:root{--red:#ff0033;--red-d:#d6002b;--purple:#8b46d9;--redbg:#fff1f3;--ink:#191919;--sub:#6f6f6f;--line:#e6e6e6;--bg:#f5f5f5;--card:#fff;
--grad:linear-gradient(90deg,#ff0033 0%,#e2245e 45%,#8b46d9 100%);
--ok:#d6002b;--okbg:#fff1f3;--ng:#3a3a3a;--ngbg:#ececec;--warn:#7a5a00;--warnbg:#fff8e5}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Noto Sans JP",system-ui,sans-serif;line-height:1.85;font-size:16px;letter-spacing:.03em;-webkit-font-smoothing:antialiased}
a{color:var(--red-d)}
.wrap{max-width:760px;margin:0 auto;padding:0 18px 64px}
header.site{background:#fff;position:sticky;top:0;z-index:5;box-shadow:0 1px 0 rgba(0,0,0,.04)}
header.site .wrap{padding-top:14px;padding-bottom:14px;display:flex;align-items:center;gap:8px}
.logo{font-weight:700;font-size:17px;text-decoration:none;color:var(--ink);display:flex;align-items:center;gap:9px;letter-spacing:.06em}
.logo .cat{width:34px;height:34px;flex:none;object-fit:contain}
.logo span{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.tagline{display:none}
.grad{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
h1{font-size:26px;line-height:1.5;margin:28px 0 12px;font-weight:700;letter-spacing:.06em}
h2{font-size:19px;margin:0 0 14px;line-height:1.45;font-weight:700;letter-spacing:.05em;position:relative;padding-top:14px}
h2::before{content:"";position:absolute;top:0;left:2px;width:34px;height:5px;background:var(--grad);transform:skewX(-30deg);border-radius:1px}
h2 small{display:none}
h3{font-size:16px;margin:16px 0 4px}
section{background:var(--card);border-radius:10px;padding:26px 24px 16px;margin-top:18px;box-shadow:0 2px 14px rgba(0,0,0,.04)}
p{margin:0 0 10px}ul{margin:0 0 10px;padding-left:1.2em}li{margin-bottom:6px}
.muted{color:var(--sub);font-size:13px}
.item{display:flex;gap:12px;align-items:flex-start;padding:14px 0;border-top:1px solid var(--line)}.item:first-of-type{border-top:0;padding-top:2px}
.badge{flex:none;font-size:12px;font-weight:700;padding:3px 12px;border-radius:99px;background:var(--okbg);color:var(--ok);margin-top:3px;white-space:nowrap;letter-spacing:.04em}
.badge.ng{background:var(--ngbg);color:var(--ng)}.badge.none{background:#efefef;color:var(--sub)}
.item .no{font-size:12px;color:var(--sub);display:block}.item .t{display:block;font-weight:500}
.item a.t{text-decoration:none;color:var(--ink)}.item a.t::after{content:" →";color:var(--red)}
.item a.t:hover{color:var(--red-d)}
.ai{background:var(--warnbg);color:var(--warn);border-radius:10px;padding:10px 14px;font-size:13px;margin-top:16px}
.toggle{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:99px;padding:4px;gap:2px;margin:14px 0 4px}
.toggle button{border:0;background:transparent;padding:8px 20px;border-radius:99px;font:inherit;font-size:13px;color:var(--sub);cursor:pointer;letter-spacing:.05em}
.toggle button[aria-pressed=true]{background:var(--red);color:#fff;font-weight:700;box-shadow:0 4px 12px rgba(255,0,51,.25)}
.detail{display:none}body.is-detail .detail{display:block}body.is-detail .easy{display:none}
.money{font-weight:700}.formal{font-size:13px;color:var(--sub);margin:0}
.meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:20px}
.tag{font-size:12px;padding:0 2px 2px;border-bottom:1.5px solid var(--ink);color:var(--ink);font-weight:500;margin-right:6px}
.steps{display:flex;margin:4px 0 6px}
.step{flex:1;text-align:center;font-size:12px;color:var(--sub);position:relative;padding-top:24px}
.step::before{content:"";position:absolute;top:4px;left:50%;transform:translateX(-50%);width:16px;height:16px;border-radius:50%;background:#d9d9d9;z-index:1}
.step::after{content:"";position:absolute;top:11px;left:50%;width:100%;height:2px;background:#d9d9d9}
.step:last-child::after{display:none}
.step.done{color:var(--ink);font-weight:700}.step.done::before{background:var(--red)}.step.done::after{background:var(--red)}
details{border-top:1px solid var(--line);padding:12px 0}details:first-of-type{border-top:0}summary{cursor:pointer;font-weight:700}
footer{font-size:12px;color:var(--sub);margin-top:36px;padding-top:20px;border-top:1px solid var(--line)}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0;justify-content:center}.chip{font:inherit;font-size:12px;padding:5px 14px;border-radius:99px;background:#fff;border:1px solid var(--line);color:var(--ink);cursor:pointer;text-decoration:none}
.chip.on{background:var(--red);border-color:var(--red);color:#fff}.chip.area{border-style:dashed}
.search{width:100%;font:inherit;font-size:16px;padding:15px 22px;border:1px solid var(--line);border-radius:99px;background:#fff;margin:6px 0 12px;box-shadow:0 2px 10px rgba(0,0,0,.04)}
.search:focus{outline:none;border-color:var(--red);box-shadow:0 0 0 3px rgba(255,0,51,.12)}
.item .tg{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}.item .tg span{font-size:11px;color:var(--sub);background:#f2f2f2;border-radius:4px;padding:0 6px}
.hero{text-align:center;padding:36px 0 10px}
.hero .kw{display:flex;justify-content:center;flex-wrap:wrap;gap:6px 14px;font-size:13px;font-weight:700;margin-bottom:18px}
.hero .kw span{border-bottom:1.5px solid var(--ink);padding-bottom:1px}
.hero h1{font-size:clamp(28px,7vw,44px);line-height:1.4;margin:0 0 16px;letter-spacing:.08em}
.hero p{color:var(--sub);font-size:14px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:22px 0 8px}
.stat{background:#fff;border-radius:10px;padding:16px 8px;text-align:center;box-shadow:0 2px 14px rgba(0,0,0,.04)}
.stat b{display:block;font-size:30px;line-height:1.2;font-weight:700;letter-spacing:.02em}.stat b small{font-size:13px;margin-left:2px;color:var(--ink);-webkit-text-fill-color:var(--ink)}
.stat span{font-size:12px;color:var(--sub)}
.ba{display:grid;gap:8px;margin:14px 0 4px}
.ba .from{background:#fff;border:1px dashed #cfcfcf;border-radius:10px;padding:12px 14px;color:var(--sub);font-size:13px}
.ba .from b,.ba .to b{display:block;font-size:11px;letter-spacing:.1em;margin-bottom:2px}
.ba .arrow{text-align:center;font-size:15px;font-weight:700;letter-spacing:.1em;line-height:1;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.ba .to{background:#fff;border-radius:10px;padding:12px 14px;font-weight:700;font-size:17px;box-shadow:0 0 0 2px rgba(255,0,51,.18)}
.ba .to b{color:var(--red-d)}
.role{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:14px}.role div{background:var(--bg);border-radius:8px;padding:10px;font-size:12px;text-align:center}.role div b{display:block;font-size:14px}
.glance{display:grid;gap:8px;margin:14px 0}.glance div{background:#fff;border-radius:10px;padding:10px 14px;box-shadow:0 2px 14px rgba(0,0,0,.04)}
.glance span{display:block;font-size:11px;color:var(--sub);letter-spacing:.1em}.glance b{font-size:16px}
.cards{display:grid;grid-template-columns:1fr;gap:12px;margin-top:6px}
@media(min-width:640px){.cards{grid-template-columns:1fr 1fr}}
.card{display:block;background:#fff;border-radius:10px;padding:16px 16px 14px;text-decoration:none;color:var(--ink);box-shadow:0 2px 14px rgba(0,0,0,.05);border-top:4px solid transparent;border-image:var(--grad) 1;border-image-slice:1 0 0 0}
.card .no{display:block;font-size:12px;color:var(--sub);margin:8px 0 2px}.card .h{font-weight:700;line-height:1.6}.card .amt{display:block;margin-top:8px;font-weight:700;color:var(--red-d)}
.fbtns{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:8px 0 10px}@media(min-width:640px){.fbtns{grid-template-columns:repeat(3,1fr)}}
.fbtn{font:inherit;font-size:14px;font-weight:700;background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 10px;text-align:left;cursor:pointer;color:var(--ink)}
.fbtn::before{content:"";display:inline-block;width:12px;height:4px;margin-right:8px;vertical-align:middle;background:var(--grad);transform:skewX(-30deg)}.fbtn.on::before{background:#fff}.fbtn.on{background:var(--red);border-color:var(--red);color:#fff}
.onlybox{display:flex;align-items:center;gap:8px;font-size:13px;margin:10px 0 0;cursor:pointer}.onlybox input{width:18px;height:18px;accent-color:var(--red)}
body.onlysm .nosm{display:none}
.bar{height:6px;background:#eee;border-radius:99px;overflow:hidden;margin-top:6px}.bar i{display:block;height:100%;background:var(--grad)}
.terms dt{font-weight:700;margin-top:14px}.terms dt small{font-weight:400;color:var(--sub);margin-left:6px}.terms dd{margin:2px 0 0}
.terms dd.src{font-size:12px;color:var(--sub)}
.pn{display:flex;justify-content:space-between;gap:10px;margin-top:16px;font-size:13px}.pn a{text-decoration:none}
nav.bn{position:fixed;left:0;right:0;bottom:0;background:#fff;box-shadow:0 -1px 0 rgba(0,0,0,.06);display:flex;z-index:9;padding-bottom:env(safe-area-inset-bottom)}
nav.bn a{flex:1;text-align:center;font-size:13px;font-weight:700;color:var(--ink);text-decoration:none;padding:16px 0 14px;line-height:1.2;position:relative;letter-spacing:.08em}nav.bn a::before{content:"";position:absolute;top:6px;left:50%;width:18px;height:3px;margin-left:-9px;background:var(--grad);transform:skewX(-30deg)}
body{padding-bottom:60px}
.minicat{position:absolute;right:16px;top:12px;width:44px;height:auto}
.footcat{display:block;width:40px;height:auto;margin:0 auto 12px;opacity:.85}
.san{border:2px solid transparent;background:linear-gradient(#fff,#fff) padding-box,var(--grad) border-box;padding:18px 20px 12px}
.san .sanh{display:flex;align-items:center;gap:8px;padding-top:0}.san .sanh::before{display:none}.san .sanh .cat{width:30px;height:30px;object-fit:contain}
.san ol{list-style:none;margin:0;padding:0}.san li{padding:8px 0;border-top:1px solid var(--line);margin:0}.san li:first-child{border-top:0}
.san li span{display:block;font-size:11px;color:var(--red-d);font-weight:700;letter-spacing:.1em}
.gacha{text-align:center}.gacha h2::before{left:50%;margin-left:-17px}
.gres{display:flex;gap:12px;align-items:center;text-align:left;background:var(--bg);border-radius:10px;padding:14px 16px;margin:10px 0 14px;min-height:72px}
.gres .gcat{width:44px;height:44px;flex:none;object-fit:contain}.gres .badge{margin:0 6px 0 0}.gres .no{display:inline;font-size:12px;color:var(--sub)}
.gres .gh{display:block;font-weight:700;color:var(--ink);text-decoration:none;margin-top:4px;line-height:1.6}.gres .gh::after{content:" →";color:var(--red)}
.gbtn{font:inherit;font-weight:700;font-size:15px;color:#fff;background:var(--red);border:0;border-radius:99px;padding:12px 32px;cursor:pointer;letter-spacing:.08em;box-shadow:0 4px 14px rgba(255,0,51,.25)}
.gbtn:active{transform:scale(.97)}.pop{animation:pop .35s ease}@keyframes pop{0%{transform:scale(.92);opacity:.3}100%{transform:scale(1);opacity:1}}
"""

CAT_SVG = '<img class="cat" src="{root}cat-face-sm.png" alt="">'  # {root} はページの深さに合わせて置き換える

TOGGLE_JS = """<script>
(function(){var b=document.body,E=document.getElementById('b-easy'),D=document.getElementById('b-detail');if(!E)return;
function s(d){b.classList.toggle('is-detail',d);E.setAttribute('aria-pressed',!d);D.setAttribute('aria-pressed',d)}
E.onclick=function(){s(false)};D.onclick=function(){s(true)}})();
(function(){var o=document.getElementById('only');if(!o)return;function f(){document.body.classList.toggle('onlysm',o.checked)}o.onchange=f;f()})();
</script>"""


def page(title: str, body: str, depth: int = 0, desc: str = "", path: str = "", og: str = "og/index.png") -> str:
    root = "../" * depth
    url = f"{SITE_URL}/{path}"
    meta = f"""<meta property="og:type" content="website"><meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc or title)}">
<meta property="og:url" content="{e(url)}"><meta property="og:image" content="{SITE_URL}/{og}?v={OG_VER}"><meta name="twitter:image" content="{SITE_URL}/{og}?v={OG_VER}">
<meta name="twitter:card" content="summary_large_image"><link rel="canonical" href="{e(url)}">
<link rel="alternate" type="application/rss+xml" title="{SITE_NAME}" href="{SITE_URL}/feed.xml">"""
    report = f"https://github.com/{REPO}/issues/new?title=" + e(f"間違いの報告：{title}")
    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}｜{SITE_NAME}</title><meta name="description" content="{e(desc or title)}">
{meta}
<link rel="icon" href="{root}favicon.png" type="image/png"><link rel="apple-touch-icon" href="{root}apple-touch-icon.png">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<header class="site"><div class="wrap"><a class="logo" href="{root}index.html">{CAT_SVG.replace("{root}", root)}<span>猫でもわかる</span>平塚市議会</a><span class="tagline">HIRATSUKA CITY COUNCIL, MADE EASY</span></div></header>
<main class="wrap">{body}
<footer><img class="footcat" src="{root}cat-sit-sm.png" alt=""><p><b>運営：元島しん</b>（平塚市議会議員・しらさぎ・無所属クラブ所属）。会派ごとの賛否は、すべての会派を同じ形で、議会だよりの記載のとおりに載せています。<a href="{root}about.html">このサイトについて</a>・<a href="{root}riyuu.html">このサイトを作った理由</a></p><p>このサイトは、平塚市が公開している資料をもとに、プログラムとAIが自動で作っています。大事な判断の前には、各ページの「元の資料」で必ず確かめてください。</p>
<p><a href="{report}">間違いを報告する</a> ・ <a href="https://github.com/{REPO}">このサイトのしくみ（GitHub）</a></p></footer>
</main>
<nav class="bn"><a href="{root}index.html">ホーム</a><a href="{root}index.html#find">探す</a><a href="{root}index.html#sessions">定例会</a><a href="{root}yogo.html">用語</a></nav>{TOGGLE_JS}</body></html>
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


def members_match(vf: dict) -> bool:
    """採決の時の会派構成（議会だよりの凡例の人数）が、今の会派構成のページと一致するか。"""
    members_of({"name": ""})  # MEMBERS を読み込む
    cur = {g["name"]: len(g["members"]) for g in MEMBERS["groups"] if not g.get("independent")}
    indep = {m["name"].replace(" ", "") for g in MEMBERS["groups"] if g.get("independent") for m in g["members"]}
    for g in vf["groups"]:
        if g.get("independent"):
            if g["name"].replace(" ", "") not in indep:
                return False
        elif cur.get(g["name"]) != g["count"]:
            return False
    return True


def render_votes(s: dict, it: dict) -> str:
    vf, v = votes_for(s["key"], it["id"])
    if not v:
        return ""
    show_members = members_match(vf)
    rows = ""
    for g in vf["groups"]:
        if g["abbr"] not in v:
            continue
        word = vote_word(v[g["abbr"]])
        cls = "ng" if "反対" in v[g["abbr"]] else ""
        mem = ("、".join(members_of(g)) if show_members else "") if not g.get("independent") else "無所属"
        label = f'{e(g["name"])}（{g["count"]}名）' if not g.get("independent") else e(g["name"])
        rows += f'<div class="item"><span class="badge {cls}">{e(word)}</span><div><span class="t">{label}</span><span class="no">{e(mem)}</span></div></div>'
    mu = (MEMBERS or {}).get("updated") or ""
    src = vf["source"]
    return f"""<section>{h2('会派ごとの賛否', 'Votes')}<p><b>{e(vote_headline(vf, v, it['result']))}</b></p>{rows}
<p class="muted">賛否は「{e(src['title'])}」の審議結果一覧によります。{f"所属議員は市議会の会派構成のページ（{e(mu)}時点）によります。会派の人数は議会だよりの記載と一致していますが、採決のときと違う場合があります。" if show_members else "この定例会のときの会派構成は今と違うため、所属議員の名前は載せていません。"}</p></section>"""


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


def item_text(it: dict, sm: dict | None) -> str:
    parts = [it["title"]]
    if sm:
        parts += [sm.get("headline", ""), sm.get("headline_detail", "")]
        parts += [p.get("easy", "") + p.get("detail", "") for p in sm.get("points", [])]
    return " ".join(parts)


def tag_html(t: dict) -> str:
    xs = [f"<span>{e(f)}</span>" for f in t["fields"]] + [f"<span>地域：{e(a)}</span>" for a in t["areas"]]
    return f'<span class="tg">{"".join(xs)}</span>' if xs else ""


def debates_for(s: dict, it: dict) -> tuple[dict | None, list[dict]]:
    mf = load_json(DATA / "minutes" / f"{s['key']}.json")
    if not mf:
        return None, []
    return mf, [d for d in mf["debates"] if d["bill"] == it["id"]]


def speaker_group(s: dict, d: dict) -> str:
    """発言の最初の段落に会派名があればそれを使う（「○○を代表し」「○○の元島しんです」）。"""
    vf = load_json(DATA / "votes" / f"{s['key']}.json")
    for g in (vf or {}).get("groups", []):
        if not g.get("independent") and g["name"] in d.get("intro", ""):
            return g["name"]
    return "無所属" if "無所属" in d.get("intro", "") else ""


def render_debates(s: dict, it: dict) -> str:
    mf, ds = debates_for(s, it)
    if mf is None:
        return ""
    src = mf["source"]
    if not ds:
        return f"""<section>{h2('討論（賛成・反対の理由）', 'Debate')}<p>本会議での討論はありませんでした。</p>
<p class="muted">出典：<a href="{e(src['url'])}">{e(src['title'])}（平塚市議会会議録）</a></p></section>"""
    rows = ""
    for d in ds:
        g = speaker_group(s, d)
        cls = "ng" if d["stance"] in ("反対",) else ""
        rows += f"""<div class="item"><span class="badge {cls}">{e(d['stance'] or '討論')}</span><div>
<span class="t">{e(d['speaker'])} 議員{f'（{e(g)}）' if g else ''}</span>
<span class="no" style="font-size:14px;color:var(--ink);margin-top:4px">「{e(d['excerpt'])}」</span></div></div>"""
    return f"""<section>{h2('討論（賛成・反対の理由）', 'Debate')}{rows}
<p class="muted">本会議の討論の一部を、会議録の文のまま抜き出しています。全文は <a href="{e(src['url'])}">{e(src['title'])}（平塚市議会会議録）</a> で読めます。</p></section>"""


def first_amount(sm):
    for p in (sm or {}).get("points", []):
        if p.get("amount"):
            return p["amount"]
    return ""


def ba_html(it, sm):
    """むずかしい正式名称 → このサイトの見出し（すぐ下のh1）、の順に見せる。"""
    if not sm:
        return f'<p class="formal">正式名称：{e(it["label"])} {e(it["title"])}</p>'
    return f'''<div class="ba" style="margin-bottom:0"><div class="from"><b>市の資料での名前</b>{e(it["label"])} {e(it["title"])}</div>
<div class="arrow">▼ つまり</div></div>'''


def glance_html(s, it, sm):
    """約3行まとめ：何が決まった・結果・だれに/お金。資料にあることだけで作る。"""
    sm = sm or {}
    rows = []
    first = ""
    if sm.get("points"):
        first = sm["points"][0].get("easy", "").split("。")[0]
        first = first + "。" if first else ""
    rows.append(("何が決まった", first or f'{it["label"]} {it["title"]}'))
    vf, v = votes_for(s["key"], it["id"])
    rows.append(("結果", vote_headline(vf, v, it["result"]) if v else (it["result"] or "報告（議会での採決はありません）")))
    amts = [p["amount"] for p in sm.get("points", []) if p.get("amount")]
    who = "、".join(w["name"] for w in sm.get("who", []))
    if who:
        rows.append(("関係する人", who))
    elif len(amts) == 1:
        rows.append(("お金", amts[0]))
    elif sm.get("unknowns"):
        rows.append(("まだ分からないこと", sm["unknowns"][0]))
    lis = "".join(f'<li><span>{e(a)}</span>{e(b)}</li>' for a, b in rows)
    return f'<section class="san"><h2 class="sanh">{CAT_SVG.replace("{root}", "../")}約3行まとめ</h2><ol>{lis}</ol></section>'


def terms_html(it, sm):
    text = item_text(it, sm) + " " + " ".join((sm or {}).get("why", []) + (sm or {}).get("numbers", []))
    ts = glossary.found_in(text + " " + (it["result"] or ""))
    if not ts:
        return ""
    lis = "".join(f'<li><a href="../yogo.html#{glossary.slug(t[0])}"><b>{e(t[0])}</b></a>：{e(t[2][:60])}{"…" if len(t[2]) > 60 else ""}</li>' for t in ts)
    return f"<section>{h2('このページに出てくる言葉', 'Glossary')}<ul>{lis}</ul></section>"


def _core(title):
    import re
    t = re.sub(r"(を求める)?(請願|意見書|陳情)$", "", title)
    return t


def related_html(s, it):
    core = _core(it["title"])
    if len(core) < 12:
        return ""
    rel = [x for x in s["items"] if x["id"] != it["id"] and _core(x["title"]) == core]
    if not rel:
        return ""
    lis = "".join(f'<li><a href="{s["key"]}-{bill_slug(x["id"])}.html">{e(x["label"])}（{e(x["result"] or "報告")}）</a></li>' for x in rel)
    return f"<section>{h2('関係する議案・請願', 'Related')}<ul>{lis}</ul></section>"


def prevnext_html(s, it):
    ids = [x["id"] for x in s["items"]]
    i = ids.index(it["id"])
    pv = s["items"][i - 1] if i > 0 else None
    nx = s["items"][i + 1] if i + 1 < len(ids) else None
    a = lambda x, t: f'<a href="{s["key"]}-{bill_slug(x["id"])}.html">{t}</a>' if x else "<span></span>"
    return f'<div class="pn">{a(pv, "← " + (pv["label"] if pv else ""))}{a(nx, (nx["label"] if nx else "") + " →")}</div>'


def render_bill(s: dict, it: dict, sm: dict | None) -> str:
    sm_ = sm or {}
    headline = sm_.get("headline") or it["title"]
    pts = ""
    for i, p in enumerate(sm_.get("points", []), 1):
        amt = f'<p>予算：<span class="money">{e(p["amount"])}</span></p>' if p.get("amount") else ""
        det = f'<p class="detail">{e(p["detail"])}</p>' if p.get("detail") else ""
        pts += f'<h3>{i}. {e(p["title"])}</h3><p class="easy">{e(p["easy"])}</p>{det}{amt}'
    calc = "".join(f"<p>{e(x)}</p>" for x in sm_.get("numbers", []))
    why = "".join(f"<p>{e(x)}</p>" for x in sm_.get("why", []))
    who = "".join(f"<li><b>{e(w['name'])}</b>：{e(w['desc'])}</li>" for w in sm_.get("who", []))
    faq = "".join(f"<details><summary>{e(q['q'])}</summary><p>{e(q['a'])}</p></details>" for q in sm_.get("faq", []))
    unk = "".join(f"<li>{e(x)}</li>" for x in sm_.get("unknowns", []))
    src = "".join(f'<li><a href="{e(x["url"])}">{e(x["title"])}</a></li>' for x in sm_.get("sources", []))
    vfile = load_json(DATA / "votes" / f"{s['key']}.json")
    if vfile:
        src += f'<li><a href="{e(vfile["source"]["pdf"])}">{e(vfile["source"]["title"])}（審議結果）</a></li>'
    t = tags_for(item_text(it, sm))
    tags = "".join(f'<span class="tag">{e(f)}</span>' for f in t["fields"]) + "".join(f'<span class="tag">地域：{e(a)}</span>' for a in t["areas"])
    if sm:
        explain = f"""<div class="toggle"><button type="button" id="b-easy" aria-pressed="true">やさしく</button><button type="button" id="b-detail" aria-pressed="false">詳しく</button></div>
<div class="ai">この説明はAIが市の資料から自動で作ったもので、人は確認していません。</div>"""
    else:
        explain = '<div class="ai">この議案のわかりやすい説明はまだありません。件名と賛否、討論だけを載せています。</div>'
    body = f"""
<div class="meta">{badge(it['result'])}<span class="tag">{e(s['name'])}</span><span class="tag">{e(KIND_LABEL.get(it['kind'], it['kind']))}</span>{tags}</div>
{ba_html(it, sm)}
<h1 class="easy" style="margin-top:6px">{e(headline)}</h1><h1 class="detail" style="margin-top:6px">{e(sm_.get('headline_detail') or headline)}</h1>
{glance_html(s, it, sm)}
{explain}
<section>{h2('審議のステータス','Status')}<div class="steps"><div class="step done">提出</div><div class="step done">委員会で審査</div><div class="step done">本会議で{e(it['result'] or '報告')}</div></div></section>
{render_votes(s, it)}
{render_debates(s, it)}
{f'<section>{h2('何が決まったの？','What was decided')}{pts}</section>' if pts else ''}
{f'<section>{h2('数字で見ると','In numbers')}{calc}</section>' if calc else ''}
{f'<section>{h2('なぜ必要なの？（市の説明）','Why')}{why}</section>' if why else ''}
{f'<section>{h2('だれに関係する？','Who is affected')}<ul>{who}</ul></section>' if who else ''}
{f'<section>{h2('よくある質問','FAQ')}{faq}</section>' if faq else ''}
{f'<section style="position:relative"><img class="minicat" src="../cat-sit-sm.png" alt="">{h2('資料からは分からないこと','Not in the documents')}<ul>{unk}</ul></section>' if unk else ''}
{terms_html(it, sm)}
{related_html(s, it)}
<section>{h2('元の資料','Sources')}<ul>{src}<li><a href="{e(s['source'])}">平塚市議会のページ</a></li></ul></section>
{prevnext_html(s, it)}
<p style="margin-top:14px"><a href="../s/{e(s['key'])}.html">← {e(s['name'])}の一覧に戻る</a></p>"""
    slug = f'{s["key"]}-{bill_slug(it["id"])}'
    vf, v = votes_for(s["key"], it["id"])
    meta = f'{s["name"]}・{it["label"]}' + (f'・{vote_headline(vf, v, it["result"])}' if v else f'・{it["result"] or ""}')
    ogp.make(OUT / "og" / "b" / f"{slug}.png", headline, meta, it["result"] or "")
    share_url = f"{SITE_URL}/b/{slug}.html"
    from urllib.parse import quote
    body += f"""<section>{h2('共有する', 'Share')}<div class="chips">
<a class="chip" href="https://x.com/intent/post?text={quote(headline)}&url={quote(share_url)}">Xで共有</a>
<a class="chip" href="https://social-plugins.line.me/lineit/share?url={quote(share_url)}">LINEで送る</a></div></section>"""
    return page(headline, body, depth=1, desc=meta, path=f"b/{slug}.html", og=f"og/b/{slug}.png")


def render_session(s: dict) -> str:
    groups = ""
    for kind in KIND_ORDER:
        items = [i for i in s["items"] if i["kind"] == kind]
        if not items:
            continue
        rows = ""
        for it in items:
            sp = summary_path(s["key"], it["id"])
            sm = load_json(sp)
            t = f'<a class="t" href="../b/{s["key"]}-{bill_slug(it["id"])}.html">{e(sm["headline"] if sm else it["title"])}</a>'
            vf, v = votes_for(s["key"], it["id"])
            vs = f'<span class="no">{e(vote_summary(vf, v))}</span>' if v else ""
            nd = len(debates_for(s, it)[1])
            vs += f'<span class="no">討論 {nd}人</span>' if nd else ""
            vs += tag_html(tags_for(item_text(it, load_json(sp))))
            rows += f'<div class="item{"" if sm else " nosm"}">{badge(it["result"])}<div><span class="no">{e(it["label"])}</span>{t}{vs}</div></div>'
        groups += f"<section>{h2(KIND_LABEL.get(kind, kind) + f'（{len(items)}件）', KIND_EN.get(kind, ''))}{rows}</section>"
    pdfs = "".join(f'<li><a href="{e(p["url"])}">{e(p["title"])}</a></li>' for p in s.get("pdfs", []))
    vf = load_json(DATA / "votes" / f"{s['key']}.json")
    dayori = f'<li><a href="{e(vf["source"]["pdf"])}">{e(vf["source"]["title"])}（審議結果・会派ごとの賛否）</a></li>' if vf else ""
    nsm = sum(1 for i in s["items"] if summary_path(s["key"], i["id"]).exists())
    body = f"""<h1>{e(s['name'])}で決まったこと</h1>
<p class="muted">全{len(s['items'])}件のうち、わかりやすい説明があるのは{nsm}件です。</p>
{'<label class="onlybox"><input type="checkbox" id="only" checked>説明があるものだけ表示</label>' if 0 < nsm < len(s['items']) else ''}
{groups}
<section>{h2('元の資料','Sources')}<ul><li><a href="{e(s['source'])}">平塚市議会 議決結果のページ</a></li>{pdfs}{dayori}</ul></section>"""
    against = sum(1 for i in s["items"] if (votes_for(s["key"], i["id"])[1] or {}) and vote_summary(*votes_for(s["key"], i["id"])) != "全会一致")
    meta = f'全{len(s["items"])}件' + (f'・反対があったもの{against}件' if load_json(DATA / "votes" / f"{s['key']}.json") else "")
    ogp.make(OUT / "og" / "s" / f"{s['key']}.png", s["name"] + "で決まったこと", meta)
    return page(s["name"] + "で決まったこと", body, depth=1, desc=meta, path=f"s/{s['key']}.html", og=f"og/s/{s['key']}.png")


def build_search_index(sessions: list[dict]) -> list[dict]:
    out = []
    for s in sessions:
        for it in s["items"]:
            sm = load_json(summary_path(s["key"], it["id"]))
            vf, v = votes_for(s["key"], it["id"])
            t = tags_for(item_text(it, sm))
            out.append({"s": s["name"], "k": s["key"], "l": it["label"], "t": it["title"],
                        "h": sm["headline"] if sm else "", "r": it["result"] or "",
                        "v": vote_summary(vf, v) if v else "", "f": t["fields"], "a": t["areas"],
                        "u": f'b/{s["key"]}-{bill_slug(it["id"])}.html'})
    return out


GACHA_JS = """<script>
(function(){var b=document.getElementById('gbtn'),r=document.getElementById('gres');if(!b)return;var data=null;
function esc(x){return String(x).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function show(){var pool=data.filter(function(d){return d.h});var d=pool[Math.floor(Math.random()*pool.length)];
 var cls=/否決|不採択|不同意|不承認|不認定/.test(d.r)?'ng':'';
 r.classList.remove('pop');void r.offsetWidth;r.classList.add('pop');
 r.innerHTML='<img src="cat-face-sm.png" alt="" class="gcat"><div><span class="badge '+cls+'">'+esc(d.r||'報告')+'</span><span class="no">'+esc(d.s+' '+d.l)+'</span><a class="gh" href="'+esc(d.u)+'">'+esc(d.h)+'</a></div>';
 b.textContent='もう一度、猫に選んでもらう'}
b.addEventListener('click',function(){if(data){show();return}b.disabled=true;
 fetch('search.json').then(function(x){return x.json()}).then(function(j){data=j;b.disabled=false;show()})});
})();
</script>"""

SEARCH_JS = """<script>
(function(){
var oq=document.getElementById('onlyq'),box=document.getElementById('q'),list=document.getElementById('results'),chips=[].slice.call(document.querySelectorAll('[data-f]'));
if(!box)return;var data=[],on=null;
function esc(x){return String(x).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function draw(){var q=box.value.trim(),hits=[];
 if(!q&&!on){list.innerHTML='';document.getElementById('latest').style.display='';return}
 document.getElementById('latest').style.display='none';
 data.forEach(function(d){var txt=[d.s,d.l,d.t,d.h,d.v,d.f.join(' '),d.a.join(' ')].join(' ');
  if(q&&q.split(/\\s+/).some(function(w){return txt.indexOf(w)<0}))return;
  if(on&&d.f.indexOf(on)<0&&d.a.indexOf(on)<0)return;if(oq&&oq.checked&&!d.h)return;hits.push(d)});
 list.innerHTML='<section><h2>'+hits.length+'件</h2>'+hits.slice(0,200).map(function(d){
  var cls=/否決|不採択|不同意|不承認|不認定/.test(d.r)?'ng':'';
  return '<div class="item"><span class="badge '+cls+'">'+esc(d.r||'報告')+'</span><div><span class="no">'+esc(d.s+' '+d.l)+'</span><a class="t" href="'+esc(d.u)+'">'+esc(d.h||d.t)+'</a>'+(d.v?'<span class="no">'+esc(d.v)+'</span>':'')+'</div></div>'}).join('')+'</section>'}
fetch('search.json').then(function(r){return r.json()}).then(function(j){data=j;draw()});
box.addEventListener('input',draw);if(oq)oq.addEventListener('change',draw);
chips.forEach(function(c){c.addEventListener('click',function(){on=(on===c.dataset.f)?null:c.dataset.f;chips.forEach(function(x){x.classList.toggle('on',x.dataset.f===on)});draw()})});
})();
</script>"""


def render_index(sessions: list[dict], last_checked: str) -> str:
    rows = ""
    for s in sessions:
        n = sum(1 for i in s["items"] if summary_path(s["key"], i["id"]).exists())
        pct = int(n * 100 / max(1, len(s["items"])))
        rows += f'<div class="item"><div style="flex:1"><a href="s/{e(s["key"])}.html"><b>{e(s["name"])}</b></a><span class="no">全{len(s["items"])}件・説明あり{n}件</span><div class="bar"><i style="width:{pct}%"></i></div></div></div>'
    cards = ""
    example = None
    if sessions:
        s = sessions[0]
        shown = 0
        def rank(it):
            sm = load_json(summary_path(s["key"], it["id"])) or {}
            return (0 if first_amount(sm) else 1, 0 if it["kind"] in ("議案", "請願") and "任命" not in it["title"] and "選任" not in it["title"] else 1)
        for it in sorted(s["items"], key=rank):
            sm = load_json(summary_path(s["key"], it["id"]))
            if not sm:
                continue
            amt = first_amount(sm)
            if example is None or (amt and not first_amount(example[1])):
                example = (it, sm)
            if shown < 6:
                cards += f'<a class="card" href="b/{s["key"]}-{bill_slug(it["id"])}.html">{badge(it["result"])}<span class="no">{e(s["name"])} {e(it["label"])}</span><span class="h">{e(sm["headline"])}</span>{f'<span class="amt">{e(amt)}</span>' if amt else ""}</a>'
                shown += 1
        more = f'<p style="margin-top:12px"><a href="s/{e(s["key"])}.html">{e(s["name"])}をすべて見る →</a></p>'
    ex = ""
    if example:
        it, sm = example
        ex = f'''<section style="position:relative"><img class="minicat" src="cat-body-sm.png" alt="">{h2('このサイトがやっていること', 'What we do')}
<p>市の資料は、正式な名前や専門の言葉で書かれています。それを、何が決まったのかが一目でわかる言葉に直しています。</p>
<div class="ba"><div class="from"><b>市の資料では</b>{e(it["label"])} {e(it["title"])}</div><div class="arrow">▼</div><div class="to"><b>このサイトでは</b>{e(sm["headline"])}</div></div>
<div class="role"><div><b>何が決まった</b>ふだんの言葉で</div><div><b>だれが賛成した</b>全会派を同じ形で</div><div><b>元の資料</b>必ずリンク</div></div></section>'''
    idx = build_search_index(sessions)
    fields = [f for f in __import__("tags").FIELDS if any(f in d["f"] for d in idx)]
    areas = sorted({a for d in idx for a in d["a"]})
    chips = "".join(f'<button type="button" class="fbtn" data-f="{e(f)}">{e(f)}</button>' for f in fields)
    achips = "".join(f'<button type="button" class="chip area" data-f="{e(a)}">{e(a)}</button>' for a in areas)
    total = sum(len(x["items"]) for x in sessions)
    explained = sum(1 for x in sessions for i in x["items"] if summary_path(x["key"], i["id"]).exists())
    body = f"""<div class="hero"><div class="kw"><span>予算</span><span>条例</span><span>請願</span><span>会派ごとの賛否</span></div>
<h1><span class="grad">猫でもわかる</span><br>平塚市議会</h1>
<p>議会って難しい言葉ばかり。<br>だから、猫でもわかる言葉に直しました。</p></div>
<div class="stats"><div class="stat"><b class="grad">{len(sessions)}<small>回</small></b><span>定例会</span></div><div class="stat"><b class="grad">{total}<small>件</small></b><span>議決・報告</span></div><div class="stat"><b class="grad">{explained}<small>件</small></b><span>説明ページ</span></div></div>
{ex}
<section id="gacha" class="gacha">{h2('猫がえらんだ議案', 'Random')}
<p class="muted">どれから読めばいいか分からない人へ。これまでの議案から、猫が1件えらびます。</p>
<div id="gres" class="gres"><img src="cat-face-sm.png" alt="" class="gcat"><span class="muted">猫はまだ、えらんでいません</span></div>
<button type="button" id="gbtn" class="gbtn">猫に選んでもらう</button></section>
<section id="find">{h2('分野・地域で探す', 'Find')}<div class="fbtns">{chips}</div><div class="chips" style="justify-content:flex-start">{achips}</div>
<input id="q" class="search" type="search" placeholder="キーワードで探す（例：保育、補聴器、公民館）" aria-label="キーワードで探す">
<label class="onlybox"><input type="checkbox" id="onlyq" checked>説明があるものだけ</label></section>
<div id="results"></div>
<div id="latest">
{f'<section>{h2('最近決まったこと','Latest')}<div class="cards">{cards}</div>{more}</section>' if cards else ''}
<section id="sessions">{h2('定例会ごとの一覧','Sessions')}{rows or '<p>まだデータがありません。</p>'}</section>
<p class="muted"><a href="yogo.html">議会の言葉の説明（用語集）</a></p>
</div>
<p class="muted">最終確認：{e(last_checked)}</p>{SEARCH_JS}{GACHA_JS}"""
    (OUT / "search.json").write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    ogp.make(OUT / "og" / "index.png", "議会って難しい言葉ばかり。だから、猫でもわかる言葉に直しました。", "平塚市議会で決まったこと・会派ごとの賛否")
    return page("議会って難しい言葉ばかり。だから、猫でもわかる言葉に直しました", body, desc="平塚市議会で可決・否決されたことと会派ごとの賛否を、市の資料をもとにわかりやすくまとめています。")


def render_feed(sessions: list[dict]) -> str:
    entries = []
    for s in sessions:
        for it in s["items"]:
            sm = load_json(summary_path(s["key"], it["id"]))
            if sm:
                entries.append((s.get("updated") or s.get("first_seen") or f'{s["key"]}-28', sm["headline"], f'{SITE_URL}/b/{s["key"]}-{bill_slug(it["id"])}.html', f'{s["name"]} {it["label"]}'))
        entries.append((s.get("updated") or s.get("first_seen") or f'{s["key"]}-28', s["name"] + "で決まったこと", f'{SITE_URL}/s/{s["key"]}.html', f'全{len(s["items"])}件'))
    entries.sort(reverse=True)
    def rfc(d):
        try:
            return datetime.fromisoformat(d if "T" in d else d + "T00:00:00+09:00").strftime("%a, %d %b %Y %H:%M:%S %z")
        except ValueError:
            return ""
    items = "".join(f"<item><title>{e(t)}</title><link>{e(u)}</link><guid>{e(u)}</guid><description>{e(dsc)}</description><pubDate>{rfc(d)}</pubDate></item>" for d, t, u, dsc in entries[:50])
    return f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{SITE_NAME}</title><link>{SITE_URL}/</link><description>平塚市議会で決まったことを、わかりやすく</description><language>ja</language>{items}</channel></rss>'


def render_about() -> str:
    body = f"""<h1>このサイトについて</h1>
<section>{h2('運営者', 'Operator')}
<p>平塚市議会議員の元島しん（平塚ユーチューバーしん）が運営しています。所属会派はしらさぎ・無所属クラブです。</p>
<p>運営者は採決に加わる議員の一人です。そのため、次のことを決まりにしています。</p>
<ul><li>会派ごとの賛否は、ひらつか議会だよりの審議結果一覧の記載のとおりに、すべての会派を同じ形で載せる</li>
<li>賛否についての評価（良い・悪い）は書かない</li>
<li>反対・賛成の理由は、会議録にある各会派の討論から、出典付きで載せる</li></ul></section>
<section>{h2('しくみ', 'How it works')}
<p>毎朝、プログラムが平塚市議会の議決結果のページ、ひらつか議会だより、会派構成のページ、会議録を読みに行き、新しい内容があればこのサイトを作り直します。議案のわかりやすい説明はAIが市の資料から書いています。</p>
<p>説明を書くときの決まりと、プログラムはすべて公開しています。<a href="https://github.com/{REPO}">GitHub</a></p></section>
<section>{h2('間違いを見つけたら', 'Report')}
<p><a href="https://github.com/{REPO}/issues/new">こちらから報告</a>してください。</p></section>"""
    return page("このサイトについて", body, path="about.html")


def render_reason() -> str:
    body = f"""<h1>猫でもわかる平塚市議会を作った理由</h1>
<p class="muted">元島しん（平塚市議会議員）</p>
<section>{h2('議会って、言葉が難しすぎる', 'Why')}
<p>「議案第82号 令和8年度平塚市一般会計補正予算」。</p>
<p>市議会の資料は、だいたいこういう名前で並んでいます。これを見て、中身が分かる人はほとんどいないと思います。</p>
<p>でも、ちゃんと読むと中身は「65歳以上の補聴器購入に、最大6万円を助成します」だったりします。暮らしに関係する話なのに、言葉が難しいせいで、誰にも届いていない。それがずっと、もったいないと思っていました。</p></section>
<section>{h2('払った税金の行き先を、知ってほしい', 'Taxes')}
<p>作った理由は、ひとことで言うとこれです。みんなが払った税金が何に使われているのかを、市民の方に知ってほしい。</p>
<p>議会では、予算も、市のルール（条例）も、大きな工事の契約も決まっています。どれも、平塚で暮らす人の生活につながっています。</p>
<p>ただ、「議会に関心を持って」と言うだけでは、関心は持ってもらえません。知りたい気持ちはあっても、入り口で引き返してしまう人が多いと思います。だったら、入り口の言葉のほうを変えよう、と考えました。</p></section>
<section>{h2('どんなサイトか', 'What')}
<p>市の資料の難しい名前を、何が決まったのかが分かる言葉に直しています。</p>
<ul><li><b>約3行まとめ</b>：どの議案も、一番上に「何が決まった」「結果」「だれに関係するか」を約3行で載せています。「約」なのは、たまに収まらないものもあるからです。</li>
<li><b>会派ごとの賛否と議員名</b>：どの会派が賛成して、どの会派が反対したかが分かります。</li>
<li><b>議員の討論</b>：賛成・反対の理由を、会議録からそのまま抜き出しています。</li>
<li><b>元の資料へのリンク</b>：全部のページに付けています。気になったら、市の資料を自分の目で確かめられます。</li>
<li><b>用語集</b>：「専決処分」「趣旨採択」みたいな議会の言葉も、ふつうの言葉で説明しています。</li></ul>
<p>令和4年12月から今年9月までの16回の定例会、489件が読めます。分野や地域で探すこともできるので、「自分の地区の公民館どうなった？」みたいな調べ方もできます。</p></section>
<section>{h2('大事にしたこと', 'Principles')}
<p>分かりやすさと同じくらい大事にしたのは、「盛らない」「えこひいきしない」ことです。</p>
<ol><li><b>資料にないことは書かない</b>：分かりやすくするために、話を足したり、大げさにしたりはしません。市の資料から分からないことは、「資料からは分からないこと」として、そのまま書いています。</li>
<li><b>全部の会派を、同じ形で載せる</b>：賛否は、議会だよりに載っているとおりに載せています。自分の会派も、自分の討論も、ほかと同じ扱いです。</li>
<li><b>誰かを評価するサイトにはしない</b>：「この議員は良い、悪い」は書きません。誰かを下げるためではなく、決まったことを知ってもらうためのサイトです。</li></ol>
<p>自分も市議会議員なので、ここがぶれると、ただの宣伝になってしまいます。そこは絶対に守りたいところです。</p></section>
<section>{h2('きっかけは「みらい議会」', 'Origin')}
<p>きっかけは、チームみらいさんの「みらい議会」です。国会の法案を分かりやすく解説しているのを見て、「これ、平塚市議会でもやりたい」と思いました。</p>
<p>運営費はほぼ0円です。プログラムが毎朝、市のページから議決結果を読みに行き、新しい結果が出たら自動でサイトに載ります。説明の文章はAIの力を借りて、市の資料をもとに作っています。だから間違いが混じることもあります。大事なことは、ページの「元の資料」で確かめてください。</p>
<p>名前は、かなり迷いました。「中学生でもわかる」「誰でもわかる！」などいろいろ考えて、最後は「猫でもわかる」にしました。議会の話は、どうしてもかたくなりがちです。せめて入り口くらいはゆるくていいかな、と。サイトのあちこちに猫がいるので、探してみてください。</p></section>
<section>{h2('ぜひ、遊びに来てください', 'Welcome')}
<p>議会のことを全部理解しなくても大丈夫です。気になる議案をひとつ、約3行だけ読んでみてください。</p>
<p>「この説明、分かりにくい」「ここ、間違ってない？」という声も大歓迎です。もらった声で、どんどん直していきます。</p>
<p><a href="index.html">トップページへ</a></p></section>"""
    return page("このサイトを作った理由", body, path="riyuu.html", desc="平塚市議会の議決を、猫でもわかる言葉に直すサイトを作った理由")


def render_glossary() -> str:
    items = ""
    for t in glossary.TERMS:
        items += f'<dt id="{glossary.slug(t[0])}">{e(t[0])}<small>{e(t[1])}</small></dt><dd>{e(t[2])}</dd><dd class="src">出典：<a href="{e(t[3][1])}">{e(t[3][0])}</a></dd>'
    body = f"""<h1>議会の言葉の説明</h1>
<p class="muted">議案や結果によく出てくる言葉を、市議会や市役所が公開している用語解説をもとに、短く言い直しています。言葉の使い方は議会によって違うことがあるので、出典もあわせて見てください。</p>
<section>{h2('用語集', 'Glossary')}<dl class="terms">{items}</dl></section>"""
    return page("議会の言葉の説明（用語集）", body, path="yogo.html", desc="専決処分、継続費、趣旨採択など、議会でよく出てくる言葉の説明")


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
            sm = load_json(summary_path(s["key"], it["id"]))
            (OUT / "b" / f"{s['key']}-{bill_slug(it['id'])}.html").write_text(render_bill(s, it, sm), encoding="utf-8")
    (OUT / "index.html").write_text(render_index(sessions, last), encoding="utf-8")
    (OUT / "about.html").write_text(render_about(), encoding="utf-8")
    (OUT / "yogo.html").write_text(render_glossary(), encoding="utf-8")
    (OUT / "riyuu.html").write_text(render_reason(), encoding="utf-8")
    for f in (ROOT / "assets").glob("*.png"):
        shutil.copy(f, OUT / f.name)
    (OUT / "feed.xml").write_text(render_feed(sessions), encoding="utf-8")
    (OUT / "CNAME").write_text(DOMAIN + "\n")
    (OUT / ".nojekyll").write_text("")
    print(f"サイトを作成: 定例会{len(sessions)}件")


if __name__ == "__main__":
    main()
