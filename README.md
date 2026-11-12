# ひらつか議会 わかる版

平塚市議会で議決されたことを、市が公開している資料をもとに自動でまとめるサイトです。

- 公開先: https://gikai.tubehira.jp
- 人による確認はしていません。間違いを見つけたら [Issue](../../issues/new) で教えてください。

## しくみ

1. GitHub Actions が毎朝、市議会の「議案名と議案概要・議決結果」ページを読みに行く（`scripts/fetch.py`）
2. 定例会ごとの一覧を `data/sessions/` に保存する。市のページは定例会ごとに上書きされるので、ここに残していく
3. `data/summaries/` にわかりやすい説明があれば、その議案のページを作る（`scripts/build.py`）
4. GitHub Pages に公開する

毎回 `data/last_checked.txt` を更新して記録するので、GitHub の「60日間動きがないと定期実行が止まる」ルールにかからない。

## データの出どころ

- ひらつか議会だより「議案等の審議結果」（会派ごとの賛否） https://www.city.hiratsuka.kanagawa.jp/gikai/page-c_02220.html
- 平塚市議会「会派・委員会の構成一覧」 https://www.city.hiratsuka.kanagawa.jp/gikai/page-c_02300.html

- 平塚市議会「議案名と議案概要・議決結果」 https://www.city.hiratsuka.kanagawa.jp/gikai/page-c_02221.html
- 平塚市「市議会提出（予定）議案」 https://www.city.hiratsuka.kanagawa.jp/keikaku/page-c_02457.html

## 文章の書き方

説明の文は `prompts/summary-rules.md` の決まりで書きます。この決まりは [yomiyasu](https://github.com/nanaism/yomiyasu)（v3.0.0、MITライセンス）の「意味を保つ」「資料にないことを足さない」考え方をもとにしています。AIが議案書を読んで説明を書くときも、この決まりを指示として渡します。
