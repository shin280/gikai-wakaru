"""data/ のJSONから静的サイトを site/ に作る。"""
import html
import re
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tags import tags_for  # noqa: E402
import ogp  # noqa: E402
import glossary
import furigana  # noqa: E402
DATA = ROOT / "data"
OUT = ROOT / "site"
DOMAIN = "gikai.tubehira.jp"
# 独自ドメインがつながるまでは GitHub Pages のアドレス。つながったら https://gikai.tubehira.jp にする
SITE_URL = "https://gikai.tubehira.jp"
# アクセス数（Supabase の gikai-wakaru-access プロジェクト。公開用のキーなので、ページに載せてよい）
SB_URL = "https://wwnerxasbcsvlvakmusg.supabase.co"
SB_KEY = "sb_publishable_BNqndJC-OfKxqQDiri9fWA_7wnOKCX6"
GC_CODE = SB_URL  # アクセス数の機能を有効にするかどうか
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
h1,.h1{font-size:26px;line-height:1.5;margin:28px 0 12px;font-weight:700;letter-spacing:.06em}
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
.detail{display:none}body.is-detail .detail{display:block}body.is-detail .easy{display:none}rt{display:none}body.kid rt::before{content:attr(data-r)}body.kid rt{display:revert;font-size:.5em;font-weight:500;color:#555}body.kid main{font-size:118%;line-height:2.2}body.kid main h1{line-height:1.9}body.kid .kh,body.kid .detail,body.kid .toggle{display:none!important}body.kid .easy{display:block!important}.kidnote{display:none}body.kid .kidnote{display:block;background:#fff8e1;border-radius:10px;padding:10px 14px;margin:10px 0;font-size:14px}.kidwrap{text-align:center;margin:18px 0}#kidbtn{background:#fff;border:2px solid var(--red);border-radius:999px;font:inherit;font-size:15px;font-weight:700;color:var(--red);padding:10px 28px;cursor:pointer}body.kid #kidbtn{background:var(--red);color:#fff}
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
.daily .drow{display:grid;grid-template-columns:44px 1fr 48px;gap:8px;align-items:center;font-size:12px;margin:3px 0}.daily i{display:block;height:10px;background:var(--grad);border-radius:3px}.daily b{text-align:right}
.more .card b{display:block;font-size:16px}.more .card span{display:block;font-size:13px;color:var(--sub);margin-top:4px}.pc{display:inline-block;margin-left:10px;font-size:13px;color:#555}.pcnote{font-size:12px}.up{background:#fff;border-radius:10px;padding:12px 16px;margin:10px 0;box-shadow:0 2px 14px rgba(0,0,0,.04)}.up h3{margin:0 0 6px;font-size:16px}.up summary{font-size:13px;color:#555;cursor:pointer}
.author{display:flex;gap:20px;align-items:center;flex-wrap:wrap;margin-top:20px}.author img{width:160px;height:160px;border-radius:50%;object-fit:cover;flex:none}.author h1{margin:0 0 6px}.author .name{font-size:22px;font-weight:700;margin:0 0 8px}.author .name small{font-size:12px;font-weight:400;color:var(--sub);margin-left:8px}
.prof th{width:6.5em;color:var(--sub);font-weight:500;vertical-align:top}.tl{list-style:none;padding:0;margin:0;border-left:3px solid var(--red);padding-left:14px}.tl li{margin:0 0 12px}.tl b{display:block;font-size:13px;color:var(--red)}.tl span{font-size:15px}
.tbl{width:100%;border-collapse:collapse;font-size:14px}.tbl th,.tbl td{padding:10px 6px;border-bottom:1px solid #eee;text-align:left}.tbl td.num,.tbl th:last-child{text-align:right;white-space:nowrap;font-weight:700}
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
[].forEach.call(document.querySelectorAll('.copyurl'),function(b){b.onclick=function(){var u=b.getAttribute('data-url');function ok(){b.textContent='コピーしました'}if(navigator.clipboard){navigator.clipboard.writeText(u).then(ok,function(){prompt('このリンクをコピーしてください',u)})}else{prompt('このリンクをコピーしてください',u)}}});
(function(){var k=document.getElementById('kidbtn');if(!k)return;function u(){var on=document.body.classList.contains('kid');var m=document.querySelector('main'),n=document.querySelector('.kidnote');if(on&&!n&&m&&window.KIDNOTE){m.insertAdjacentHTML('afterbegin',KIDNOTE)}k.textContent=on?'小学生モードをやめる':'小学生モード';k.setAttribute('aria-pressed',on)}
k.onclick=function(){var on=document.body.classList.toggle('kid');try{localStorage.setItem('kid',on?'1':'0')}catch(e){}u();window.scrollTo(0,0)};u()})();
(function(){var o=document.getElementById('only');if(!o)return;function f(){document.body.classList.toggle('onlysm',o.checked)}o.onchange=f;f()})();
</script>"""


PAGES: list = []
TITLES: dict = {}
AUTHOR = {"@type": "Person", "name": "元島しん", "jobTitle": "平塚市議会議員", "url": f"{SITE_URL}/author.html", "image": f"{SITE_URL}/shin.jpg",
          "affiliation": {"@type": "GovernmentOrganization", "name": "平塚市議会"}, "sameAs": ["https://tubehira.jp/", "https://www.youtube.com/channel/UC3cnDK33dOxD3wBxF7PZrJw"]}


def crumbs(*items) -> dict:
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": n, "item": f"{SITE_URL}/{u}"} for i, (n, u) in enumerate([("ホーム", "")] + list(items), 1)]}


GC_TAG = ("<script>(function(){if(navigator.webdriver)return;var p=location.pathname;if(p==='/index.html')p='/';"
          "try{var k='hv'+new Date().toISOString().slice(0,10)+p;if(localStorage.getItem(k))return;localStorage.setItem(k,'1')}catch(e){}"
          f"fetch('{SB_URL}/rest/v1/rpc/hit',{{method:'POST',keepalive:true,headers:{{apikey:'{SB_KEY}','Content-Type':'application/json'}},body:JSON.stringify({{p:p}})}}).catch(function(){{}})"
          "})();</script>")


def render_access(sessions) -> str:
    titles = json.dumps({k: v for k, v in TITLES.items()}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    body = f"""<h1>アクセス数</h1>
<p class="muted">このサイトがどれくらい見られているかを、そのまま公開しています。同じ人が同じ日に同じページを何度開いても、1回と数えます。</p>
<section>{h2('見られた回数', 'Page views')}<div class="stats">
<div class="stat"><b id="c-today">…</b><span>今日</span></div><div class="stat"><b id="c-week">…</b><span>この7日間</span></div><div class="stat"><b id="c-month">…</b><span>この30日間</span></div></div>
<p class="muted" id="c-total"></p></section>
<section>{h2('毎日の回数（30日間）', 'Daily')}<div id="c-daily" class="daily"></div></section>
<section>{h2('よく見られているページ', 'Top pages')}<table class="tbl" id="c-top"><tr><th>ページ</th><th>回数</th></tr></table></section>
<section>{h2('数え方', 'How')}<p>ページを開いたときに「どのページが、いつ開かれたか」だけを記録しています。IPアドレス、名前、メールアドレスなど、人を見分けられる情報は記録していません。Cookieも使っていません。</p></section>
<script>
(function(){{var T={titles};
function n(x){{return Number(x).toLocaleString('ja-JP')}}
function esc(t){{var d=document.createElement('div');d.textContent=t;return d.innerHTML}}
fetch('{SB_URL}/rest/v1/rpc/stats',{{method:'POST',headers:{{apikey:'{SB_KEY}','Content-Type':'application/json'}},body:'{{}}'}}).then(function(r){{return r.json()}}).then(function(d){{
document.getElementById('c-today').textContent=n(d.today);document.getElementById('c-week').textContent=n(d.week);document.getElementById('c-month').textContent=n(d.month);
document.getElementById('c-total').textContent='数え始めた日（'+(d.since||'-')+'）からの合計：'+n(d.total)+'回';
var mx=1;d.daily.forEach(function(x){{if(x.v>mx)mx=x.v}});
document.getElementById('c-daily').innerHTML=d.daily.length?d.daily.map(function(x){{return '<div class="drow"><span>'+x.d.slice(5).replace('-','/')+'</span><i style="width:'+Math.max(2,x.v/mx*100)+'%"></i><b>'+n(x.v)+'</b></div>'}}).join(''):'<p class="muted">まだ記録がありません。</p>';
document.getElementById('c-top').innerHTML+=d.top.map(function(x){{var u=x.p==='/'?'index.html':x.p.slice(1);return '<tr><td><a href="'+esc(u)+'">'+esc(T[x.p]||T[(function(){{try{{return decodeURIComponent(x.p)}}catch(e){{return x.p}}}})()]||x.p)+'</a></td><td class="num">'+n(x.v)+'</td></tr>'}}).join('');
}}).catch(function(){{document.getElementById('c-total').textContent='いま数字を読み込めません。時間をおいて開いてください。'}})}})();
</script>"""
    return page("アクセス数", body, path="access.html", desc="猫でもわかる平塚市議会のアクセス数", ld=[crumbs(("アクセス数", "access.html"))])


def share_html(text: str, url: str) -> str:
    from urllib.parse import quote
    t = text if SITE_NAME in text else f"{text}｜{SITE_NAME}"
    return f"""<section class="share">{h2('共有する', 'Share')}<div class="chips" style="justify-content:flex-start">
<a class="chip" href="https://x.com/intent/post?text={quote(t)}&url={quote(url)}">Xで共有</a>
<a class="chip" href="https://social-plugins.line.me/lineit/share?url={quote(url)}">LINEで送る</a>
<a class="chip" href="https://www.facebook.com/sharer/sharer.php?u={quote(url)}">Facebookで共有</a>
<button type="button" class="chip copyurl" data-url="{e(url)}">リンクをコピー</button></div></section>"""


def write_llms(sessions):
    """AI（ChatGPT、Claude、Perplexity など）が読みやすいように、サイトの中身をテキストでまとめる。"""
    head = f"""# {SITE_NAME}

> 平塚市議会（神奈川県平塚市）で可決・否決されたこと、会派ごとの賛否を、市の公開資料をもとに、中学生にもわかる言葉で説明しているサイトです。運営は元島しん（平塚市議会議員）。説明はプログラムとAIで市の資料から作っています。正確な内容は各ページの「元の資料」（平塚市の公式資料）で確かめてください。

- 掲載範囲：{sessions[-1]['name'] if sessions else ''}から{sessions[0]['name'] if sessions else ''}まで、{len(sessions)}回の定例会、{sum(len(x['items']) for x in sessions)}件
- 会派ごとの賛否は、すべての会派を同じ形で、「ひらつか議会だより」の記載のとおりに載せています
- 更新：毎日、平塚市議会の「議決結果」のページを確かめて自動で更新

## 主なページ
- [トップ]({SITE_URL}/)
- [これから決まること（次の定例会）]({SITE_URL}/kore.html)
- [地区・地名から探す]({SITE_URL}/area/index.html)
- [議会に参加する（傍聴・中継・請願）]({SITE_URL}/sanka.html)
- [議会の言葉の説明（用語集）]({SITE_URL}/yogo.html)
- [このサイトについて]({SITE_URL}/about.html)\n- [作った人（元島しん、平塚市議会議員）]({SITE_URL}/author.html)
- [全議案の説明（テキスト）]({SITE_URL}/llms-full.txt)

## 定例会
"""
    head += "".join(f"- [{x['name']}で決まったこと]({SITE_URL}/s/{x['key']}.html)：{len(x['items'])}件\n" for x in sessions)
    (OUT / "llms.txt").write_text(head, encoding="utf-8")
    full = [head.split("## 主なページ")[0]]
    for x in sessions:
        full.append(f"\n## {x['name']}\n出典：{x.get('source', '')}\n")
        for it in x["items"]:
            sm = load_json(summary_path(x["key"], it["id"]))
            vf, v = votes_for(x["key"], it["id"])
            res = vote_headline(vf, v, it["result"]) if v else (it["result"] or "報告")
            url = f"{SITE_URL}/b/{x['key']}-{bill_slug(it['id'])}.html"
            full.append(f"\n### {sm['headline'] if sm else it['title']}\n- 正式な件名：{it['label']} {it['title']}\n- 結果：{res}\n")
            if sm:
                for p in sm.get("points", []):
                    if p.get("easy"):
                        full.append(f"- {p.get('title', '')}：{p['easy']}" + (f"（金額：{p['amount']}）" if p.get("amount") else "") + "\n")
            full.append(f"- くわしく：{url}\n")
    (OUT / "llms-full.txt").write_text("".join(full), encoding="utf-8")


KIDNOTE = '<p class="kidnote">小学生モード：漢字にふりがなを付けて、大事なところだけ見せています。ふりがなはコンピューターが自動で付けているので、読みがちがうことがあります。もとにもどすときは、ページの一番下のボタンをおしてください。</p>'


def page(title: str, body: str, depth: int = 0, desc: str = "", path: str = "", og: str = "og/index.png", ld: list | None = None, full_title: str = "") -> str:
    PAGES.append(path)
    TITLES['/' + path if path else '/'] = title
    root = "../" * depth
    from urllib.parse import quote as _q
    url = f"{SITE_URL}/{_q(path)}"
    meta = f"""<meta property="og:type" content="website"><meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc or title)}">
<meta property="og:url" content="{e(url)}"><meta property="og:image" content="{SITE_URL}/{og}?v={OG_VER}"><meta name="twitter:image" content="{SITE_URL}/{og}?v={OG_VER}">
<meta name="twitter:card" content="summary_large_image"><link rel="canonical" href="{e(url)}">
<link rel="alternate" type="application/rss+xml" title="{SITE_NAME}" href="{SITE_URL}/feed.xml">"""
    if ld:
        meta += "".join('<script type="application/ld+json">' + json.dumps(x, ensure_ascii=False).replace("</", "<\\/") + "</script>" for x in ld)
    report = f"https://github.com/{REPO}/issues/new?title=" + e(f"間違いの報告：{title}")
    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title or (title + "｜" + SITE_NAME))}</title><meta name="description" content="{e(desc or title)}">
{meta}
<link rel="icon" href="{root}favicon.png" type="image/png"><link rel="apple-touch-icon" href="{root}apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap" rel="stylesheet">
<style>{CSS}</style>{GC_TAG if GC_CODE else ''}</head><body>
<script>try{{if(localStorage.getItem('kid')==='1')document.body.classList.add('kid')}}catch(e){{}}</script>
<header class="site"><div class="wrap"><a class="logo" href="{root}index.html">{CAT_SVG.replace("{root}", root)}<span>猫でもわかる</span>平塚市議会</a><span class="tagline">HIRATSUKA CITY COUNCIL, MADE EASY</span></div></header>
<main class="wrap">{furigana.add(body)}{share_html(title if path else SITE_NAME, url) if path != "404.html" else ""}
<footer><img class="footcat" src="{root}cat-sit-sm.png" alt=""><p><b>運営：<a href="{root}author.html">元島しん</a></b>（平塚市議会議員・しらさぎ・無所属クラブ所属）。会派ごとの賛否は、すべての会派を同じ形で、議会だよりの記載のとおりに載せています。<a href="{root}about.html">このサイトについて</a>・<a href="{root}riyuu.html">このサイトを作った理由</a>・<a href="{root}author.html">作った人</a></p><p><a href="{root}kore.html">これから決まること</a>・<a href="{root}area/index.html">地区・地名から探す</a>・<a href="{root}sanka.html">議会に参加する</a></p><p>このサイトは、平塚市が公開している資料をもとに、プログラムとAIが自動で作っています。大事な判断の前には、各ページの「元の資料」で必ず確かめてください。</p>
<p class="kidwrap"><button type="button" id="kidbtn" aria-pressed="false">小学生モード</button></p>
<p><a href="{report}">間違いを報告する</a>{(' ・ <a href="' + root + 'access.html">アクセス数</a>') if GC_CODE else ''} ・ <a href="https://github.com/{REPO}">このサイトのしくみ（GitHub）</a></p></footer>
</main>
<nav class="bn"><a href="{root}index.html">ホーム</a><a href="{root}index.html#find">探す</a><a href="{root}index.html#sessions">定例会</a><a href="{root}yogo.html">用語</a></nav><script>var KIDNOTE={json.dumps(furigana.add(KIDNOTE), ensure_ascii=False).replace('</', '<\\/')};</script>{TOGGLE_JS}</body></html>
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
        pc = per_capita(amts[0])
        rows.append(("お金", amts[0] + (f"（市民1人あたり {pc}）" if pc else "")))
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


DUP_HEADLINES: set = set()


def render_bill(s: dict, it: dict, sm: dict | None) -> str:
    sm_ = sm or {}
    headline = sm_.get("headline") or it["title"]
    pts = ""
    for i, p in enumerate(sm_.get("points", []), 1):
        pc = per_capita(p.get("amount", ""))
        amt = (f'<p>予算：<span class="money">{e(p["amount"])}</span>' + (f'<span class="pc">市民1人あたり {pc}</span>' if pc else '') + '</p>') if p.get("amount") else ""
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
    tags = "".join(f'<span class="tag">{e(f)}</span>' for f in t["fields"]) + "".join(f'<a class="tag" href="../area/{e(a)}.html">地域：{e(a)}</a>' for a in t["areas"])
    if sm:
        explain = f"""<div class="toggle"><button type="button" id="b-easy" aria-pressed="true">やさしく</button><button type="button" id="b-detail" aria-pressed="false">詳しく</button></div>
"""
    else:
        explain = '<div class="ai">この議案のわかりやすい説明はまだありません。件名と賛否、討論だけを載せています。</div>'
    body = f"""
<div class="meta">{badge(it['result'])}<span class="tag">{e(s['name'])}</span><span class="tag">{e(KIND_LABEL.get(it['kind'], it['kind']))}</span>{tags}</div>
<div class="kh">{ba_html(it, sm)}</div>
<h1 class="easy" style="margin-top:6px">{e(headline)}</h1><p class="detail h1" style="margin-top:6px">{e(sm_.get('headline_detail') or headline)}</p>
{glance_html(s, it, sm)}
{explain}
<section class="kh">{h2('審議のステータス','Status')}<div class="steps"><div class="step done">提出</div><div class="step done">委員会で審査</div><div class="step done">本会議で{e(it['result'] or '報告')}</div></div></section>
<div class="kh">{render_votes(s, it)}
{render_debates(s, it)}</div>
{f'<section>{h2('何が決まったの？','What was decided')}{pts}{PC_NOTE if 'class="pc"' in pts else ''}</section>' if pts else ''}
{f'<section class="kh">{h2('数字で見ると','In numbers')}{calc}</section>' if calc else ''}
{f'<section class="kh">{h2('なぜ必要なの？（市の説明）','Why')}{why}</section>' if why else ''}
{f'<section>{h2('だれに関係する？','Who is affected')}<ul>{who}</ul></section>' if who else ''}
{f'<section class="kh">{h2('よくある質問','FAQ')}{faq}</section>' if faq else ''}
{f'<section class="kh" style="position:relative"><img class="minicat" src="../cat-sit-sm.png" alt="">{h2('資料からは分からないこと','Not in the documents')}<ul>{unk}</ul></section>' if unk else ''}
<div class="kh">{terms_html(it, sm)}
{related_html(s, it)}</div>
<section class="kh">{h2('元の資料','Sources')}<ul>{src}<li><a href="{e(s['source'])}">平塚市議会のページ</a></li></ul>{('<p class="muted">このページの更新：<time datetime="' + s['updated'][:10] + '">' + str(int(s['updated'][:4])) + '年' + str(int(s['updated'][5:7])) + '月' + str(int(s['updated'][8:10])) + '日</time></p>') if s.get('updated') else ''}</section>
{prevnext_html(s, it)}
<p style="margin-top:14px"><a href="../s/{e(s['key'])}.html">← {e(s['name'])}の一覧に戻る</a></p>"""
    slug = f'{s["key"]}-{bill_slug(it["id"])}'
    vf, v = votes_for(s["key"], it["id"])
    meta = f'{s["name"]}・{it["label"]}' + (f'・{vote_headline(vf, v, it["result"])}' if v else f'・{it["result"] or ""}')
    ogp.make(OUT / "og" / "b" / f"{slug}.png", headline, meta, it["result"] or "")
    first = ((sm_.get("points") or [{}])[0].get("easy") or "").split("。")[0]
    res = vote_headline(vf, v, it["result"]) if v else (it["result"] or "報告")
    desc = (first + "。" if first else "") + f'平塚市議会{s["name"]}の{it["label"]}「{it["title"]}」。結果：{res}。'
    if len(desc) > 120:  # 長すぎるときは正式な件名を省く（件名は本文と構造化データに残る）
        desc = (first + "。" if first else "") + f'平塚市議会{s["name"]}の{it["label"]}。結果：{res}。'
    ld = [crumbs((s["name"], f"s/{s['key']}.html"), (it["label"], f"b/{slug}.html")),
          {"@context": "https://schema.org", "@type": "Article", "headline": headline[:110], "description": desc,
           "image": f"{SITE_URL}/og/b/{slug}.png", "inLanguage": "ja", "author": AUTHOR,
           "publisher": {"@type": "Organization", "name": SITE_NAME, "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/apple-touch-icon.png"}},
           "mainEntityOfPage": f"{SITE_URL}/b/{slug}.html", "about": f'{it["label"]} {it["title"]}',
           "datePublished": s.get("first_seen", ""), "dateModified": s.get("updated", ""),
           "isBasedOn": [x for x in [s.get("source")] + [d.get("url") for d in s.get("pdfs", [])] if x],
           "sourceOrganization": {"@type": "GovernmentOrganization", "name": "平塚市議会", "url": "https://www.city.hiratsuka.kanagawa.jp/gikai/"}}]
    qa = [(f"{it['label']}「{it['title']}」で何が決まった？", " ".join(p.get("easy", "") for p in sm_.get("points", []) if p.get("easy"))),
          (f"{it['label']}「{it['title']}」の結果は？", f"{s['name']}で{res}。")]
    qa = [(q, a) for q, a in qa if a.strip()]
    if qa:
        ld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qa]})
    # 同じ見出しの議案がほかにもあるときは、title に定例会と番号を足して区別する
    full = f'{headline}（{s["name"]}・{it["label"]}）' if headline in DUP_HEADLINES else ""
    if not full and len(headline) > 48:  # 長い見出しは、サイト名を付けずに title にする（検索結果で途中で切れないように）
        full = headline
    return page(headline, body, depth=1, desc=desc, path=f"b/{slug}.html", og=f"og/b/{slug}.png", ld=ld, full_title=full)


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
    desc = f'平塚市議会{s["name"]}で決まったこと（{meta}）。議案・請願ごとに、何が決まったかをわかりやすい言葉で説明しています。'
    return page(f'平塚市議会 {s["name"]}で決まったこと', body, depth=1, desc=desc, path=f"s/{s['key']}.html", og=f"og/s/{s['key']}.png",
                ld=[crumbs((s["name"], f"s/{s['key']}.html"))])


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
    achips = "".join(f'<a class="chip area" href="area/{e(a)}.html">{e(a)}</a>' for a in areas) + '<a class="chip area" href="area/index.html">地区・地名の一覧</a>'
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
<section>{h2('もっと知る', 'More')}<div class="cards more"><a class="card" href="kore.html"><b>これから決まること</b><span>次の定例会に出される議案と日程</span></a><a class="card" href="area/index.html"><b>地区・地名から探す</b><span>自分の地区で決まったこと</span></a><a class="card" href="sanka.html"><b>議会に参加する</b><span>傍聴・ネット中継・請願の出し方</span></a></div></section>
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
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": f"{SITE_URL}/", "inLanguage": "ja",
           "description": "平塚市議会で決まったことを、わかりやすい言葉で説明するサイト", "author": AUTHOR}]
    return page(SITE_NAME, body, desc="平塚市議会の議案・予算・条例・請願で何が決まったかを、わかりやすい言葉で説明。会派ごとの賛否、議員の討論、市の資料へのリンクも。令和4年12月からの定例会を掲載。",
                ld=ld, full_title=f"{SITE_NAME}｜平塚市議会で決まったことを、わかりやすく")


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
<p>どのページが何回見られたかを数えて、<a href="access.html">アクセス数のページ</a>で公開しています。記録するのはページと日付だけで、人を見分けられる情報は記録していません。</p>
<p>説明を書くときの決まりと、プログラムはすべて公開しています。<a href="https://github.com/{REPO}">GitHub</a></p></section>
<section>{h2('間違いを見つけたら', 'Report')}
<p><a href="https://github.com/{REPO}/issues/new">こちらから報告</a>してください。</p></section>"""
    return page("このサイトについて", body, path="about.html", desc="猫でもわかる平塚市議会の運営者・しくみ・掲載の決まり", ld=[crumbs(("このサイトについて", "about.html"))])


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
    ld = [crumbs(("このサイトを作った理由", "riyuu.html")),
          {"@context": "https://schema.org", "@type": "Article", "headline": "猫でもわかる平塚市議会を作った理由", "inLanguage": "ja",
           "author": AUTHOR, "image": f"{SITE_URL}/og/index.png", "mainEntityOfPage": f"{SITE_URL}/riyuu.html"}]
    return page("このサイトを作った理由", body, path="riyuu.html", desc="平塚市議会の議決を、猫でもわかる言葉に直すサイトを作った理由", ld=ld)



# ---- 市民1人あたり ----
POP = 257320
POP_DATE = "令和8年7月1日現在"
POP_SRC = ("平塚市「人口速報ひらつか」", "https://www.city.hiratsuka.kanagawa.jp/common/200205503.pdf")


def yen(s: str):
    """「15億7,717万3,400円」「6万6千円」などを円の数にする。マイナスや読めないものは None。"""
    if not s or "マイナス" in s or "△" in s:
        return None
    t = s.replace(",", "").replace("，", "").strip()
    m = re.fullmatch(r"(?:(\d+)億)?(?:(\d+)万)?(?:(\d+)千)?(\d+)?円", t)
    if not m or not any(m.groups()):
        return None
    oku, man, sen, rest = (int(x) if x else 0 for x in m.groups())
    return oku * 10**8 + man * 10**4 + sen * 1000 + rest


def per_capita(amount: str) -> str:
    v = yen(amount)
    if not v:
        return ""
    pc = v / POP
    if pc >= 10:
        return f"約{round(pc):,}円"
    if pc >= 1:
        return f"約{pc:.1f}円"
    return ""


PC_NOTE = f'<p class="muted pcnote">※「市民1人あたり」は、金額を平塚市の人口{POP:,}人（{POP_DATE}、<a href="{POP_SRC[1]}">{POP_SRC[0]}</a>）で割った目安です。</p>'


# ---- 一覧の1行 ----
def item_row(s: dict, it: dict, prefix: str = "../") -> str:
    sm = load_json(summary_path(s["key"], it["id"]))
    vf, v = votes_for(s["key"], it["id"])
    vs = f'<span class="no">{e(vote_summary(vf, v))}</span>' if v else ""
    return (f'<div class="item">{badge(it["result"])}<div><span class="no">{e(s["name"])} {e(it["label"])}</span>'
            f'<a class="t" href="{prefix}b/{s["key"]}-{bill_slug(it["id"])}.html">{e(sm["headline"] if sm else it["title"])}</a>{vs}</div></div>')


# ---- 地区ごとのページ ----
def area_entries(sessions):
    out = {}
    for s in reversed(sessions):
        for it in s["items"]:
            for a in tags_for(item_text(it, load_json(summary_path(s["key"], it["id"]))))["areas"]:
                out.setdefault(a, []).append((s, it))
    return out


def render_area(place: str, entries: list, upcoming_hits: list) -> str:
    rows = "".join(item_row(s, it) for s, it in entries)
    up = ""
    if upcoming_hits:
        up = f'<section>{h2("これから決まること", "Upcoming")}<ul>' + "".join(f'<li>{e(x.get("easy") or x["title"])}</li>' for x in upcoming_hits) + '</ul><p><a href="../kore.html">これから決まること（一覧）</a></p></section>'
    body = f"""<h1>{e(place)}で決まったこと</h1>
<p class="muted">議案や請願の件名・説明に「{e(place)}」という地名が出てくるものを集めています。地名が書かれていない議案（市全体の予算など）でも、{e(place)}に関係することがあります。</p>
{up}<section>{h2(f'{len(entries)}件', 'Decided')}{rows}</section>
<p><a href="index.html">ほかの地区・地名を見る</a></p>"""
    return page(f"平塚市{place}で決まったこと（市議会）", body, depth=1, path=f"area/{place}.html",
                desc=f"平塚市議会で決まったことのうち、「{place}」が出てくる議案・請願{len(entries)}件をわかりやすく。",
                ld=[crumbs(("地区・地名から探す", "area/index.html"), (place, f"area/{place}.html"))])


def render_area_index(areas: dict) -> str:
    chips = "".join(f'<a class="chip area" href="{e(a)}.html">{e(a)}（{len(v)}）</a>' for a, v in sorted(areas.items(), key=lambda x: -len(x[1])))
    body = f"""<h1>地区・地名から探す</h1>
<p class="muted">議案や請願の件名・説明に出てくる地名ごとにまとめています。（ ）の数字は件数です。</p>
<div class="chips" style="justify-content:flex-start">{chips}</div>"""
    return page("地区・地名から探す", body, depth=1, path="area/index.html", desc="平塚市議会で決まったことを、真土・大神・四之宮など地区や地名ごとにまとめています。",
                ld=[crumbs(("地区・地名から探す", "area/index.html"))])


# ---- これから決まること ----
def load_upcoming(sessions):
    done = {s["key"] for s in sessions}
    ups = sorted((load_json(p) for p in (DATA / "upcoming").glob("*.json")), key=lambda d: d["key"]) if (DATA / "upcoming").exists() else []
    ups = [u for u in ups if u and u["key"] not in done]
    return ups[-1] if ups else None


def render_upcoming(up) -> str:
    if not up:
        body = """<h1>これから決まること</h1><p>次の定例会の予定が出たら、ここに載せます。</p>"""
        return page("これから決まること", body, path="kore.html")
    sched = "".join(f'<tr><td>{e(x["d"])}</td><td>{e(x["what"])}</td></tr>' for x in up.get("schedule", []))
    items = ""
    for x in up.get("items", []):
        det = "".join(f"<li>{e(d)}</li>" for d in x.get("details", []))
        easy = f'<p class="easy" style="display:block">{e(x["easy"])}</p>' if x.get("easy") else ""
        items += f"""<div class="up"><h3>{e(x['title'])}</h3>{easy}<details><summary>市の説明（そのまま）</summary><p>{e(x['overview'])}</p>{f'<ul>{det}</ul>' if det else ''}</details></div>"""
    if items:
        lead = f'<p>市が発表した、{e(up["name"])}に出される予定の議案です。結果が出たら、ほかの議案と同じように説明ページを作ります。</p>'
        if not any(x.get("easy") for x in up["items"]):
            lead += '<p class="muted">やさしい説明は準備中です。いまは市の説明をそのまま載せています。</p>'
        items = f'<section>{h2(f"出される予定の議案（{len(up["items"])}件）", "Bills")}{lead}{items}<p class="muted">出典：<a href="{e(up["press"])}">平塚市 記者発表「市議会定例会の提出案件」</a></p></section>'
    else:
        items = f'<section>{h2("出される予定の議案", "Bills")}<p>市が議案の一覧を発表したら、ここに載せます。前回（令和8年9月定例会）は、定例会が始まる6日前に、市長の記者会見で発表されました。</p></section>'
    body = f"""<h1>これから決まること</h1>
<p class="muted">次の定例会（{e(up['name'])}）で話し合われることです。{('会期は' + e(up['kaiki']) + 'です。') if up.get('kaiki') else ''}</p>
{items}
{f'<section>{h2("日程", "Schedule")}<table class="tbl">{sched}</table><p class="muted">日程は変わることがあります。出典：<a href="{e(up["schedule_source"])}">平塚市議会「会議の日程」と傍聴のご案内</a></p></section>' if sched else ''}
<section>{h2('見に行く・意見を伝える', 'Join')}<p>本会議はだれでも傍聴でき、インターネットでも見られます。<a href="sanka.html">参加のしかた</a></p></section>"""
    return page(f"これから決まること（{up['name']}）", body, path="kore.html",
                desc=f"平塚市議会{up['name']}に出される予定の議案と日程を、結果が出る前にわかりやすく。")


# ---- 参加ガイド ----
GUIDE_SRC = {
    "bocho": "https://www.city.hiratsuka.kanagawa.jp/gikai/page-c_02369.html",
    "chukei": "https://www.city.hiratsuka.kanagawa.jp/gikai/page-c_02288.html",
    "seigan": "https://www.city.hiratsuka.kanagawa.jp/gikai/page-c_02222.html",
    "giin": "https://www.city.hiratsuka.kanagawa.jp/gikai/page-c_02299.html",
}


def render_guide() -> str:
    g = GUIDE_SRC
    body = f"""<h1>議会に参加する</h1>
<p class="muted">議会は、見ることも、意見を伝えることもできます。平塚市議会のページに書かれていることを、やさしい言葉でまとめました。くわしいことや最新の情報は、それぞれの「元のページ」で確かめてください。</p>
<section>{h2('ネットやテレビで見る', 'Watch')}
<ul><li>本会議は、インターネットで生中継されています。あとから録画も見られます（会議のおよそ7日後から、会議録が市のサイトに載るまで）。<a href="https://hiratsuka-city.stream.jfit.co.jp/">平塚市議会 インターネット中継</a></li>
<li>ケーブルテレビ（湘南ケーブルネットワーク、デジタル002チャンネル）でも、本会議を生中継しています。</li></ul>
<p class="muted">元のページ：<a href="{g['chukei']}">市議会のテレビ・インターネット中継</a></p></section>
<section>{h2('傍聴する（会議を直接見に行く）', 'Visit')}
<ul><li><b>本会議</b>：だれでも見に行けます。市役所本館8階の傍聴受付で、住所と名前を書きます。先着順で、席は97人分（車いす席5席をふくむ）です。</li>
<li><b>小さい子どもと一緒でも大丈夫</b>：乳幼児を連れた人のための部屋が2つあります（1部屋3人くらい）。</li>
<li><b>耳が聞こえにくい人</b>：聞こえを助ける機械を5台貸し出しています。受付で伝えてください。手話通訳は、見に行きたい日の3週間前までに申し込みます。</li>
<li><b>議案の資料</b>：傍聴する人に貸し出しています。</li>
<li><b>委員会</b>：委員長の許可があれば見られます。席は18人分です。</li>
<li><b>守ること</b>：拍手やヤジはだめです。席での飲食・たばこはできません。携帯電話は音が出ないようにします。写真・録音・録画は原則できません。</li>
<li>10人以上のグループで行くときは、前もって議会局議事担当（0463-21-8791）に連絡します。</li></ul>
<p>次の定例会の日程は<a href="kore.html">これから決まること</a>にも載せています。</p>
<p class="muted">元のページ：<a href="{g['bocho']}">平塚市議会「会議の日程」と傍聴のご案内</a></p></section>
<section>{h2('請願・陳情を出す（お願いを議会に届ける）', 'Petition')}
<p>市にしてほしいことを、文書にして議会に出せます。出し方は2つあります。</p>
<ul><li><b>請願</b>：議員1人以上に「紹介議員」として名前を書いてもらう必要があります。委員会で話し合い、本会議で「採択（認める）」か「不採択（認めない）」かを決めます。結果は出した人（代表者）に知らされます。</li>
<li><b>陳情</b>：紹介議員はいりません。多くは議会運営委員会で扱いを話し合います。その結果は、出した人には知らされません（市長の担当の内容は、市から回答が来ることがあります）。</li></ul>
<p><b>書き方</b>：日付、住所、あて先（平塚市議会議長）を書き、署名するか、名前を書いてはんこを押します。団体のときは、団体名と代表者の名前を書きます。書き方の見本は元のページにあります。</p>
<p><b>出す場所</b>：市役所本館8階の議会局。</p>
<p><b>しめきり（午後5時まで）</b>：請願は、定例会の本会議2日目まで。陳情は、議会運営委員会の2日前（土・日・祝日をのぞく）まで。</p>
<p><b>知っておくこと</b>：出した請願・陳情は、全部の議員に写しが配られます。請願書と陳情書は情報公開の対象です（いっしょに出した署名簿は公開されません）。請願を出した人は、本会議3日目の正午までに申し出れば、委員会で5分以内、意見を話せることがあります。</p>
<p class="muted">元のページ：<a href="{g['seigan']}">請願・陳情の提出方法</a>　問い合わせ：議会局議事担当 0463-21-8791</p></section>
<section>{h2('議員に連絡する', 'Contact')}
<p>平塚市議会の「議員一覧」に、議員ごとの名前・会派・住所・電話番号が載っています（事務所の住所・電話のこともあります）。メールアドレスは載っていません。</p>
<p class="muted">元のページ：<a href="{g['giin']}">議員一覧</a></p></section>"""
    return page("議会に参加する（傍聴・中継・請願・議員への連絡）", body, path="sanka.html",
                desc="平塚市議会を見に行く（傍聴）、ネットで見る、請願・陳情を出す、議員に連絡する方法を、やさしい言葉で。",
                ld=[crumbs(("議会に参加する", "sanka.html"))])



def render_author() -> str:
    YT = "https://www.youtube.com/channel/UC3cnDK33dOxD3wBxF7PZrJw"
    rows = [("名前", "元島しん（もとしま しん）"), ("活動名", "平塚ユーチューバーしん"), ("生まれ", "1997年、埼玉県行田市"),
            ("住まい", "平塚市（2018年から）"), ("学歴", "日本電子専門学校 卒業"), ("家族", "息子と2人暮らしのシングルファザー"),
            ("仕事", "平塚市議会議員（2023年に初当選、1期目）"), ("会派", "しらさぎ・無所属クラブ"),
            ("委員会", "総務経済常任委員会 副委員長、ICT推進委員会（2026年9月現在）"), ("好きなこと", "ポケモンカード、動画づくり")]
    tbl = "".join(f"<tr><th>{e(a)}</th><td>{e(b)}</td></tr>" for a, b in rows)
    hist = [("2018年", "平塚市に引っ越してきて、起業"), ("2019年", "YouTubeチャンネル「平塚ユーチューバーしん」を始める"),
            ("2020年", "テイクアウト専門の惣菜店「おそうざいのGEKIRIN」を市内に開く"), ("2022年", "ポケモンカード専門店「GEKIRIN湘南平塚店」を開く"),
            ("2023年", "平塚市議会議員に初当選"), ("2025年7月", "株式会社GEKIRINを退職し、議員の仕事に専念"),
            ("2026年11月", "「猫でもわかる平塚市議会」を公開")]
    tl = "".join(f'<li><b>{e(a)}</b><span>{e(b)}</span></li>' for a, b in hist)
    body = f"""<div class="author"><img src="shin.jpg" alt="元島しんの写真" width="240" height="240">
<div><h1>作った人</h1><p class="name">元島しん<small>もとしま しん</small></p>
<p>平塚市議会議員。YouTubeの「平塚ユーチューバーしん」として、平塚のお店や街の変化を動画で伝えています。</p></div></div>
<section>{h2('プロフィール', 'Profile')}<table class="tbl prof">{tbl}</table></section>
<section>{h2('これまで', 'History')}<ol class="tl">{tl}</ol></section>
<section>{h2('議会で取り組んでいること', 'Work')}
<ul><li>子育て・教育</li><li>ひとり親の支え</li><li>まちづくり</li><li>市の情報の伝え方をよくすること</li></ul>
<p>議会での質問や市への確認を通して、市民の声と市政をつなぐことを大事にしています。</p></section>
<section>{h2('YouTube', 'YouTube')}
<p>2019年から「平塚ユーチューバーしん」として、平塚のお店の開店・閉店や街の話題を動画にしています。</p>
<p><a class="chip" href="{YT}">YouTubeチャンネルを見る</a></p></section>
<section>{h2('なぜこのサイトを作ったか', 'Why')}
<p>みんなが払った税金が何に使われているのかを、市民の方に知ってほしいからです。議会の資料は言葉が難しすぎて、暮らしに関係する話なのに届いていない。だったら、入り口の言葉のほうを変えようと思いました。</p>
<p>お店をやっていたときも、YouTubeでも、「平塚のことを、平塚の人に、わかる言葉で伝える」ことをずっとやってきました。このサイトは、それを議会でもやってみたものです。</p>
<p><a href="riyuu.html">このサイトを作った理由（くわしく）</a></p></section>
<section>{h2('このサイトで守っていること', 'Promise')}
<ul><li>市の資料にないことは書きません。</li>
<li>会派ごとの賛否は、すべての会派を同じ形で載せています。自分の会派も、ほかと同じ扱いです。</li>
<li>誰かを良い・悪いと評価するサイトにはしません。</li></ul></section>
<section>{h2('連絡', 'Contact')}
<p>「ここが分かりにくい」「間違っている」という声は、ページの一番下の「間違いを報告する」から送れます。</p>
<p><a href="https://tubehira.jp/">元島しんの公式サイト</a></p>
<p class="muted">プロフィールは、本人の公式サイトに載せている内容をもとにしています。</p></section>"""
    person = {"@context": "https://schema.org", "@type": "ProfilePage", "mainEntity": {**AUTHOR, "alternateName": "平塚ユーチューバーしん",
              "memberOf": {"@type": "Organization", "name": "しらさぎ・無所属クラブ"}, "birthDate": "1997", "birthPlace": "埼玉県行田市", "alumniOf": "日本電子専門学校", "homeLocation": "神奈川県平塚市"}}
    return page("作った人（元島しん）", body, path="author.html", desc="猫でもわかる平塚市議会を作った、平塚市議会議員・元島しんのページ",
                ld=[crumbs(("作った人", "author.html")), person])


def render_glossary() -> str:
    items = ""
    for t in glossary.TERMS:
        items += f'<dt id="{glossary.slug(t[0])}">{e(t[0])}<small>{e(t[1])}</small></dt><dd>{e(t[2])}</dd><dd class="src">出典：<a href="{e(t[3][1])}">{e(t[3][0])}</a></dd>'
    body = f"""<h1>議会の言葉の説明</h1>
<p class="muted">議案や結果によく出てくる言葉を、市議会や市役所が公開している用語解説をもとに、短く言い直しています。言葉の使い方は議会によって違うことがあるので、出典もあわせて見てください。</p>
<section>{h2('用語集', 'Glossary')}<dl class="terms">{items}</dl></section>"""
    dts = {"@context": "https://schema.org", "@type": "DefinedTermSet", "name": "議会の言葉の説明（用語集）", "url": f"{SITE_URL}/yogo.html",
           "hasDefinedTerm": [{"@type": "DefinedTerm", "name": t[0], "description": t[2], "url": f"{SITE_URL}/yogo.html#{glossary.slug(t[0])}"} for t in glossary.TERMS]}
    return page("議会の言葉の説明（用語集）", body, path="yogo.html", desc="専決処分、継続費、趣旨採択など、議会でよく出てくる言葉の説明", ld=[crumbs(("用語集", "yogo.html")), dts])


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
    from collections import Counter
    hc = Counter((load_json(summary_path(s["key"], it["id"])) or {}).get("headline") or it["title"] for s in sessions for it in s["items"])
    DUP_HEADLINES.update(h for h, n in hc.items() if n > 1)
    for s in sessions:
        (OUT / "s" / f"{s['key']}.html").write_text(render_session(s), encoding="utf-8")
        for it in s["items"]:
            sm = load_json(summary_path(s["key"], it["id"]))
            (OUT / "b" / f"{s['key']}-{bill_slug(it['id'])}.html").write_text(render_bill(s, it, sm), encoding="utf-8")
    (OUT / "index.html").write_text(render_index(sessions, last), encoding="utf-8")
    (OUT / "about.html").write_text(render_about(), encoding="utf-8")
    (OUT / "yogo.html").write_text(render_glossary(), encoding="utf-8")
    (OUT / "riyuu.html").write_text(render_reason(), encoding="utf-8")
    (OUT / "author.html").write_text(render_author(), encoding="utf-8")
    up = load_upcoming(sessions)
    (OUT / "kore.html").write_text(render_upcoming(up), encoding="utf-8")
    (OUT / "sanka.html").write_text(render_guide(), encoding="utf-8")
    (OUT / "area").mkdir(exist_ok=True)
    areas = area_entries(sessions)
    for a, ents in areas.items():
        hits = [x for x in (up or {}).get("items", []) if a in x["title"] + x.get("overview", "") + " ".join(x.get("details", []))]
        (OUT / "area" / f"{a}.html").write_text(render_area(a, ents, hits), encoding="utf-8")
    (OUT / "area" / "index.html").write_text(render_area_index(areas), encoding="utf-8")

    if GC_CODE:
        (OUT / "access.html").write_text(render_access(sessions), encoding="utf-8")
    for f in list((ROOT / "assets").glob("*.png")) + list((ROOT / "assets").glob("*.jpg")):
        shutil.copy(f, OUT / f.name)
    (OUT / "404.html").write_text(page("ページが見つかりません", '<h1>ページが見つかりません</h1><p>このページはなくなったか、URLが違うようです。</p><p><a href="/index.html">トップページへ</a></p>', path="404.html").replace('<meta charset="utf-8">', '<meta charset="utf-8"><meta name="robots" content="noindex">', 1), encoding="utf-8")
    PAGES.remove("404.html")
    from urllib.parse import quote as _q
    urls = "".join(f"<url><loc>{SITE_URL}/{_q(u)}</loc></url>" for u in PAGES)
    (OUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>', encoding="utf-8")
    bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User", "PerplexityBot", "Perplexity-User", "Google-Extended", "Applebot-Extended", "Bingbot"]
    (OUT / "robots.txt").write_text("".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots) + f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")
    write_llms(sessions)
    (OUT / "feed.xml").write_text(render_feed(sessions), encoding="utf-8")
    (OUT / "CNAME").write_text(DOMAIN + "\n")
    (OUT / ".nojekyll").write_text("")
    print(f"サイトを作成: 定例会{len(sessions)}件")


if __name__ == "__main__":
    main()
