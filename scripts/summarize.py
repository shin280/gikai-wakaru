"""議案書などのPDFをAI（Claude）に読ませ、議案ごとのわかりやすい説明を data/summaries/ に保存する。

- 指示には prompts/summary-rules.md をそのまま使う。
- 書いたあと、同じPDFをもう一度AIに見せて、文の中の数字が資料にあるかを確かめさせ、
  見つからない数字を含む文は捨てる。
- APIキー（環境変数 ANTHROPIC_API_KEY）がなければ何もしない。サイトの更新は止めない。
"""
import base64
import io
import json
import os
import re
import sys
from pathlib import Path

import requests
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RULES = (ROOT / "prompts" / "summary-rules.md").read_text(encoding="utf-8")
MODEL = os.environ.get("SUMMARY_MODEL", "claude-sonnet-5-5")
MAX_BILLS_PER_RUN = int(os.environ.get("MAX_BILLS_PER_RUN", "60"))  # 1回の実行で書く上限（費用の歯止め）
PAGES_PER_CALL = 90  # 1回に渡すPDFのページ数（APIの上限100ページより少なめ）
TARGET_KINDS = {"議案", "会議案", "認"}
UA = "gikai-wakaru (+https://github.com/shin280/gikai-wakaru)"

SCHEMA = """{
  "id": "議案82 のような、渡した一覧のid",
  "headline": "やさしい見出し（何が決まったかを一文で。40字程度まで）",
  "headline_detail": "正式な用語での見出し",
  "points": [{"title": "小見出し", "easy": "やさしい説明", "detail": "正式な用語での説明", "amount": "金額（あれば。なければ空文字）"}],
  "numbers": ["数字で見るとわかること（資料の数字だけ）"],
  "why": ["市の説明する理由（資料にあれば）"],
  "who": [{"name": "関係する人", "desc": "どう関係するか"}],
  "faq": [{"q": "住民が持ちそうな疑問", "a": "資料にある答え"}],
  "unknowns": ["資料からは分からないこと"],
  "evidence_pages": [元の資料でのページ番号]
}"""


def client():
    import anthropic
    return anthropic.Anthropic()


def pdf_chunks(data: bytes):
    """PDFを PAGES_PER_CALL ページずつに分けて (開始ページ, PDFのbytes) を返す。"""
    reader = PdfReader(io.BytesIO(data))
    n = len(reader.pages)
    for start in range(0, n, PAGES_PER_CALL):
        w = PdfWriter()
        for i in range(start, min(n, start + PAGES_PER_CALL)):
            w.add_page(reader.pages[i])
        buf = io.BytesIO()
        w.write(buf)
        yield start + 1, buf.getvalue()


def ask(c, pdf: bytes, prompt: str, max_tokens: int = 16000) -> str:
    msg = c.messages.create(
        model=MODEL, max_tokens=max_tokens,
        messages=[{"role": "user", "content": [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                            "data": base64.standard_b64encode(pdf).decode()}},
            {"type": "text", "text": prompt}]}])
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


def parse_json(text: str):
    m = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    raw = m.group(1) if m else text[text.find("["): text.rfind("]") + 1]
    return json.loads(raw)


def write_prompt(bills: list[dict], session_name: str, first_page: int) -> str:
    listing = "\n".join(f'- id={b["id"]} / {b["label"]} {b["title"]}（結果：{b["result"] or "報告"}）' for b in bills)
    return f"""あなたは平塚市議会で議決された議案を、平塚市民向けにわかりやすく説明する文を書きます。
添付のPDFは「{session_name}」の市の資料の一部です（このPDFの1ページ目は、元の資料の{first_page}ページ目です）。

次の決まりを必ず守ってください。

{RULES}

## 対象の議案
次の一覧のうち、添付のPDFに中身（条文、提案理由、金額など）が載っている議案だけについて書いてください。
載っていない議案は出力に含めないでください。

{listing}

## 出力
JSONの配列だけを ```json のコードブロックで出力してください。要素の形は次のとおりです。
不明なことは推測せず unknowns に入れてください。points は1〜3個にしてください。
{SCHEMA}
"""


def verify_prompt(items: list[dict]) -> str:
    return f"""添付のPDFは市の資料です。次のJSONは、この資料をもとにAIが書いた議案の説明です。
説明の文の中にある数字（金額・日付・件数・人数・割合など）を1つずつ、資料の中に同じ値（単位の言い換えは同じとみなす。
例：79,423千円＝7,942万3千円）があるか確かめてください。
資料に見つからない数字、または資料と違う数字を含む文を、すべて挙げてください。

出力はJSONの配列だけを ```json のコードブロックで出してください。要素は {{"id": "議案のid", "text": "問題のある文をそのまま", "reason": "理由"}} です。
問題がなければ [] を出してください。

{json.dumps(items, ensure_ascii=False)}
"""


def drop_sentences(sm: dict, bad_texts: set[str]) -> dict:
    """数字の照合で引っかかった文を取り除く。見出しが引っかかったら、その議案は丸ごと捨てる。"""
    if sm.get("headline") in bad_texts:
        return {}
    sm = dict(sm)
    sm["points"] = [p for p in sm.get("points", []) if p.get("easy") not in bad_texts and p.get("detail") not in bad_texts]
    for k in ("numbers", "why", "unknowns"):
        sm[k] = [x for x in sm.get(k, []) if x not in bad_texts]
    sm["faq"] = [q for q in sm.get("faq", []) if q.get("a") not in bad_texts]
    if sm.get("headline_detail") in bad_texts:
        sm["headline_detail"] = ""
    return sm if sm["points"] else {}


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY がないので、AIによる説明づくりは飛ばします。")
        return 0
    c = client()
    budget = MAX_BILLS_PER_RUN
    for sp in sorted((DATA / "sessions").glob("*.json"), reverse=True):
        s = json.loads(sp.read_text(encoding="utf-8"))
        outdir = DATA / "summaries" / s["key"]
        todo = [i for i in s["items"] if i["kind"] in TARGET_KINDS and not (outdir / f'{i["id"]}.json').exists()]
        if not todo or not s.get("pdfs"):
            continue
        print(f'{s["name"]}: 説明のない議案 {len(todo)}件')
        for pdf in s["pdfs"]:
            todo = [i for i in todo if not (outdir / f'{i["id"]}.json').exists()]
            if not todo or budget <= 0:
                break
            data = requests.get(pdf["url"], headers={"User-Agent": UA}, timeout=120).content
            for first, chunk in pdf_chunks(data):
                if budget <= 0:
                    break
                bills = [i for i in todo if not (outdir / f'{i["id"]}.json').exists()][:budget]
                if not bills:
                    break
                try:
                    drafts = parse_json(ask(c, chunk, write_prompt(bills, s["name"], first)))
                except Exception as ex:  # 1つ失敗しても残りは続ける
                    print(f'  {pdf["title"]} p{first}〜: 書けませんでした（{ex}）', file=sys.stderr)
                    continue
                ids = {b["id"] for b in bills}
                drafts = [d for d in drafts if d.get("id") in ids and d.get("headline") and d.get("points")]
                if not drafts:
                    continue
                try:
                    bad = parse_json(ask(c, chunk, verify_prompt(drafts), 8000))
                except Exception as ex:
                    print(f'  照合に失敗したので、この分は保存しません（{ex}）', file=sys.stderr)
                    continue
                bad_by_id = {}
                for b in bad:
                    bad_by_id.setdefault(b.get("id"), set()).add(b.get("text", ""))
                outdir.mkdir(parents=True, exist_ok=True)
                for d in drafts:
                    sm = drop_sentences(d, bad_by_id.get(d["id"], set()))
                    if not sm:
                        print(f'  {d["id"]}: 数字の照合で見出しか全部のポイントが落ちたので保存しません')
                        continue
                    pages = [p for p in d.get("evidence_pages", []) if isinstance(p, int)]
                    sm.pop("evidence_pages", None)
                    sm.pop("id", None)
                    label = pdf["title"] + (f'（{min(pages)}ページなど）' if pages else "")
                    sm["sources"] = [{"title": label, "url": pdf["url"]}]
                    sm["generated_by"] = MODEL
                    (outdir / f'{d["id"]}.json').write_text(json.dumps(sm, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    budget -= 1
                    print(f'  {d["id"]}: 保存（落とした文 {len(bad_by_id.get(d["id"], set()))}）')
    return 0


if __name__ == "__main__":
    sys.exit(main())
