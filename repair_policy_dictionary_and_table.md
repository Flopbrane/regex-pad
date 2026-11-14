# 辞書参照とテーブルブロックの改修方針

作成日: 2026-11-13  
対象: Regex-Pad と wp-conv  
関連: `troubleshooting_table_block_errors.md`

## 決定した原則

**利用者が挿入・編集する完成形のスクリプトは、該当する辞書エントリを正本とする。** Python は辞書の読込・検証、値の差し込み、選択範囲・カーソル・Undo/Redo、表の行列生成を担当する。同じ用途の完成タグを Python に重ねて固定しない。

一方、HTML や Gutenberg の構文を**認識・検査**するための正規表現、タグ名、ブロック名などはコード内に残せる。変換器が可変個数の行やセルを組み立てる処理もコードの責務である。辞書化するのは、その処理が出力する表の外枠・セルの装飾など、利用者に見える変更可能なテンプレート部分から始める。辞書を通しただけで WordPress 互換になるわけではないため、出力形式は実際の Gutenberg 保存結果で検証する。

資料 `PARAGRAPH_INSERT_DICTIONARY_PLAN.md` は調査前の提案として参照した。以下の範囲と優先順位は、現在のソースを確認して決めたものである。

## 確認した呼び出し経路

| 操作・用途 | 現在の経路 | 辞書の状況 | 判断 |
| --- | --- | --- | --- |
| Regex-Pad の通常のタグ挿入（メニュー、右クリック、`Ctrl+Shift+T` ダイアログ） | `main.py` → `editor/tag_insert.py` の `tag_snippet_groups()` → `TagSnippet.render()` | `dictionaries/html_dict.json` の `tag.html.paragraph`、`dictionaries/wordpress_html_dict.json` の `tag.wordpress.paragraph_block` などを既に使用 | この経路は維持。新しい段落辞書を重複作成しない |
| Regex-Pad の段落分割後の前後段落 | `main.py` の段落分割アクション → `editor/paragraph_splitter.py` の `_replace_current_paragraph_selection()` → `build_paragraph_block()` | `build_paragraph_block()` が `wp:paragraph` と `<p>` の完成形をコードに固定 | 既存 `tag.wordpress.paragraph_block` を参照させる第一候補 |
| 段落分割で挿入するスペーサー | `build_spacer_block()` | 既存 `tag.wordpress.spacer_block` は高さ 30px、現行分割処理は 32px。カーソル位置も異なる | 見た目を変えずに辞書を拡張するか、分割専用のエントリを既存 WordPress 辞書に追加 |
| 段落分割で挿入する HTML コード枠 | `build_html_code_block()` | 既存 `tag.wordpress.html_code_box` と CSS・空内容時のカーソル位置が違う | 既存エントリを無理に流用せず、分割専用エントリを既存 WordPress 辞書に追加 |
| 段落分割で挿入する装飾枠 | `_build_decorated_block()` → `wordpress_tag_snippet()` | 既に `tag.wordpress.info_frame_block` を参照 | この方式を維持 |
| Regex-Pad の WordPress 表のタグ挿入 | `tag.wordpress.table_block` | `wordpress_html_dict.json` に存在 | `troubleshooting_table_block_errors.md` の検証結果に基づき、標準表と装飾 Custom HTML 表のエントリを分ける |
| Regex-Pad の Markdown 表変換 | `wp_conv_core/wp_blocks/wp_table.py` | 行列から `wp:table` 外枠とセル HTML を Python で生成 | 行列処理は維持。出力形式・外枠の正本を辞書化する範囲を決め、タグ挿入と矛盾させない |
| wp-conv の表変換 | `blocks/table.py`、`converters/markdown_converter.py`、`converters/html_converter.py` | 標準表の外枠を Python で生成。スタイル付き表を Custom HTML に保つ未コミット変更あり | その変更を保持し、同じ表出力ポリシーに合わせる。既存入力の属性や内容を落とさない |

`paragraph_insert_dict.json` は**現時点では新設しない**。段落の通常挿入には既存辞書があり、段落分割専用の差異も同じ WordPress 辞書に用途別キーを足す方が所在を一つに保てるためである。辞書の構造が不足することを具体的なテストで確認した場合のみ、新規ファイルを再検討する。

## 改修順序

### 1. 失敗・成功例を固定する

前回のテーブル記録から、手書き `style` を足して無効になった `wp:table` と、罫線付きで表示できた `wp:html` を対にする。段落分割は、現在の入力・出力、カーソル位置、Undo/Redo を基準例にする。どちらを先に実装してもよいが、各経路で現行結果を確定してから変更する。

### 2. Regex-Pad の段落分割を辞書参照にする

- `build_paragraph_block()` が使う完成タグを `tag.wordpress.paragraph_block` から取得する。辞書の `{selection}` に分割前後の本文を入れ、`{cursor}` を削除する。HTML の本文は既にエスケープや `<br>` を含む場合があるため、二重エスケープや文字列の欠落を起こさない。
- 段落分割専用のスペーサーとコード枠は、現在の 32px・CSS・空内容・カーソル位置を保つ辞書エントリを既存 `wordpress_html_dict.json` に追加する。必要な場合のみ表示文言を追加し、通常のタグ挿入メニューへ意図せず増やさない。
- 辞書読込失敗・キー欠落・不正な `{selection}` / `{cursor}` では、編集前にエラーを返し、本文・選択範囲・Undo 履歴を変更しない。`main.py` の既存の `ParagraphSplitError` 表示経路を使う。
- 現行 `PARAGRAPH_TAG_PATTERN` は `<p>` の属性を受け取るが、再生成時には属性を落とす。段落分割で属性付き段落をどう扱うかを先にテストで固定し、属性保持ができない形なら安全に中止する。これは辞書参照とは別の内容消失リスクである。

### 3. テーブルの出力ポリシーを両プロジェクトに適用する

- **標準表**: Gutenberg が保存して再編集できる `wp:table` の形を、対象 WordPress 版で実測する。`hasFixedLayout` の既定値と `has-fixed-layout`、見出し・本文・セルタグを揃える。Regex-Pad の表挿入辞書と両変換器の出力を同じ検証例で比較する。
- **装飾表**: 幅、セル罫線、背景色などを保持する必要がある場合は、辞書に定義した明示的な `wp:html` 形式を選ぶ。行列生成は Python で行うが、装飾と外枠は辞書由来にする。任意の入力 HTML は属性・キャプション・結合セルを捨てて単純表に再構成しない。
- Regex-Pad の表挿入辞書にある現行 `wp:table` は、Gutenberg の実保存形式と照合してから修正する。600px と水色は装飾表の選択肢であり、全表の既定値にしない。
- wp-conv の既存のスタイル付き表を `wp:html` に保つ未コミット変更を取り込む形で進める。Regex-Pad と wp-conv の辞書は各配布物に同梱し、同じ意図のキー・テンプレート・検証例を共有する。実行時に他方のプロジェクトのファイルを参照しない。

### 4. ほかの固定スクリプトを棚卸しする

今回確認できた `build_spacer_block()`、`build_html_code_block()` のほか、wp-conv の段落・表ビルダー、Regex-Pad 内の WordPress 表ビルダーなど、**利用者へ出力する完成形**を列挙する。すべてを一度に辞書へ移すのではなく、壊れた/直った実例がある経路から修正する。`main.py` の `<strong>`・`<u>` のインライン装飾も固定文字列だが、今回の段落分割・テーブルとは別の操作であるため後続の棚卸し対象とする。

## 受け入れ条件

1. 段落タグのテンプレートを辞書で変更した時、通常のタグ挿入と段落分割の該当出力に反映される。専用のスペーサー・コード枠は既存の表示とカーソル位置を維持する。
2. 未選択、選択あり、複数行、日本語、HTML 特殊文字、空行で本文が失われない。操作一回の Undo/Redo も維持する。
3. 辞書欠落・不正 JSON・キー欠落・不正テンプレートは、安全に失敗して元原稿を変更しない。利用者に原因が分かる。
4. テーブルの壊れた/直った対では、対象診断が壊れた側のみに出る。ほかの無関係な警告がゼロであることまでは要求しない。
5. `wp:table` は実際の WordPress エディターで貼付→保存→再読込→再編集を通す。`wp:html` は幅・罫線・スマートフォンでのスクロールを公開表示で確認する。Regex-Pad のプレビューだけでは合格としない。
6. 指定 Python 環境で関連テスト・Ruff・Pyright を実行する。辞書のパス解決と配布物への同梱を確認する。EXE を実際に組み直していない場合は EXE 動作を未確認と明記する。

## 現時点の境界

本書は**改修方針**であり、コード改修・Gutenberg での再編集・EXE の実機確認はまだ実施していない。`wp_converter` の既存の未コミット変更は保持する。修正実施時は各プロジェクトの `SCRIPT_STEP.md` に変更内容と検証結果を残す。
