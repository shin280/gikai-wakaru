"""説明ページの文を1つのMarkdownにまとめて標準出力に出す（yomiyasu の検査用）。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for f in sorted((ROOT / "data" / "summaries").glob("*/*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    print(f"## {f.parent.name} {f.stem}\n\n{d['headline']}\n")
    for p in d.get("points", []):
        print(f"### {p['title']}\n\n{p['easy']}\n")
    for x in d.get("numbers", []) + d.get("why", []):
        print(x + "\n")
