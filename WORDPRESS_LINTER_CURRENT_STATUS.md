# RegexPad WordPress Linter 現状整理

作成日: 2026-11-16  
対象プロジェクト: `D:\PC\Python\regex_pad_project`

## 1. 結論

現在のRegexPadに実装されているのは、次の二層です。

1. **本文消失やブロック破損につながる構造エラーを検出する安全Linter**
2. **実際のWordPress保存結果で確認できた範囲だけを照合する、部分的なJSON・class・style Linter**

一方、次のものではありません。

- Gutenbergの完全な代替検証器
- WordPress全バージョンのブロック保存処理の再実装
- `theme.json`、全コアブロック、全プラグインブロックを含む完全互換Linter
- Gutenbergが行う `save()` 検証や「ブロックに予期しない内容が含まれています」の完全再現

したがって、RegexPadの現在の役割は、次のように定義するのが適切です。

> **WordPressへ貼り付ける前に、危険な構造事故を見つける。確認済みの装飾については補助的に整合性を確認する。最終的なGutenberg互換性は、本物のWordPressで確認する。**

## 2. 現在の検査を三段階に分ける

| 段階 | 担当 | 現在の状態 |
|---|---|---|
| 第1段階 | HTML・WordPressブロックの構造安全性 | 実装済み。RegexPadの中心機能 |
| 第2段階 | 確認済みJSON・class・styleの対応 | 13ブロックについて部分実装済み |
| 第3段階 | Gutenbergでの保存・再読込・再編集 | RegexPad外。実際のWordPressで確認 |

処理の考え方は次のとおりです。

```text
記事ソース
  ↓
RegexPad: HTML・ブロック境界・親子構造を検査
  ↓
RegexPad: 確認済みのJSON/class/styleだけを補助検査
  ↓
WordPress: Gutenbergで保存・再読込・再編集を確認
```

第1段階は独立した安全検査として価値があります。第2段階が未対応のブロックでも、第1段階の構造検査は利用できます。

## 3. 現在、実用的に検出できるもの

### 3.1 HTML構造

現在のHTML Linterは、主に次を検出します。

- 開始タグと終了タグの不足
- 終了タグの順序違い
- 対応する開始タグがない終了タグ
- インラインタグを親要素の終了前に閉じていない状態
- HTMLタグ名の入力ミスと候補
- HTML属性名の入力ミスと候補
- 属性が開始タグの外へ飛び出した状態
- 複数行タグの壊れた属性継続
- タグに使用できない属性
- 全角の `<`、`>`、`=`、引用符、全角空白など、HTML構文を壊す文字
- 制限対象のタグやイベント属性
- HTMLコメント内の見本コードを実タグと誤認しないための抑制

### 3.2 CSSと `style=""`

インラインCSSについて、主に次を検査します。

- CSS構文エラー
- 未知のプロパティ
- 単位の典型的な入力ミス
- プロパティ名の典型的な入力ミス
- 複数行 `style` の実際の行番号
- WordPressプリセット変数を含む確認済みstyle値の不一致

ただし、ブラウザーの全CSS仕様、テーマによる上書き、詳細なカスケード計算までは再現しません。

### 3.3 WordPressブロックコメント

次のようなブロック境界問題を検出できます。

- `<!-- wp:... -->` に対応する終了コメントがない
- 開始コメントがない `<!-- /wp:... -->`
- 開始ブロック名と終了ブロック名の不一致
- ブロックコメントの順序交差
- JSON部分の構文エラー
- JSON部分がオブジェクトではない
- 既知ブロック名の入力ミスと候補
- 同じ非入れ子ブロックを誤って重ねた状態
- HTMLタグがWordPressブロック境界をまたいでいる状態
- `wp:html` 内部へ別のWordPressブロックコメントが混入した状態
- エスケープされたブロックコメント断片の混入

これらは、本文消失やGutenbergでのブロック破損に直結しやすい検査です。

### 3.4 親子関係と非コンテナブロック

現在、次の必須親関係を明示的に検査します。

| 子ブロック | 必須親ブロック |
|---|---|
| `accordion-item` | `accordion` |
| `accordion-heading` | `accordion-item` |
| `accordion-panel` | `accordion-item` |
| `button` | `buttons` |
| `column` | `columns` |
| `list-item` | `list` |

また、次の親は許可する直接子を限定しています。

- `accordion`
- `accordion-item`
- `buttons`
- `columns`
- `list`

`paragraph`、`heading`、`separator`、`spacer`、`image` は非コンテナとして扱い、その内部へ別のブロックを入れた場合の危険な構造を検出します。

### 3.5 ブロック固有のHTML形状

次のブロックでは、ブロックコメント内部のルートHTMLタグも検査します。

| ブロック | 確認する主なルートタグ |
|---|---|
| Paragraph | `p` |
| Heading | `h1`～`h6` |
| Group | `div`、`section`、`article`などコア対応タグ |
| Buttons / Button | `div` |
| Quote | `blockquote` |
| Pullquote | `figure` |
| Accordion一式 | `div`、Headingのみ `h1`～`h6` |
| Columns / Column | `div` |
| Separator | `hr` または `div` |
| List / List item | `ul`・`ol` / `li` |

Paragraphでは、`p` の開始・終了不足や、段落内部へ `div` を混入した状態も別途検出します。

### 3.6 選択されたブロック属性

現在のWordPressブロックスキーマには23ブロックが登録されています。

```text
paragraph, heading, image, spacer, table, list, list-item, group,
html, media-text, columns, column, quote, pullquote, accordion,
accordion-item, accordion-heading, accordion-panel, separator,
code, preformatted, buttons, button
```

このスキーマにより、登録済み属性について次を検査できます。

- 未知の属性名
- 属性名の入力ミス候補
- boolean、integer、object、arrayなどの基本型
- 一部属性の列挙値や数値範囲
- Headingのレベルと実際のHTML見出しタグ
- Spacerの高さ
- Imageの一部サイズ属性
- Paragraphの一部typography・preset対応

23ブロックが登録されていることは、23ブロックの保存形式を完全検証できるという意味ではありません。属性名と基本型だけを知っているブロックも含まれます。

## 4. JSON・class・style照合の実装範囲

### 4.1 確認済み対応表があるブロック

実際のWordPress保存結果を根拠にした対応表は、現在13ブロックです。

```text
group
paragraph
buttons
button
quote
pullquote
accordion
accordion-item
accordion-heading
accordion-panel
columns
column
separator
```

対応表では、規則を次の種類に分けています。

- JSON属性から必要になるclass
- JSON属性から必要になるinline style
- JSONには存在するが、同じ値をinline styleへ繰り返さない属性
- ルート要素ではなく、Buttonの内側のリンクなどに付くclass/style
- `fitText: true` のような特定値のときだけ必要になるclass

### 4.2 確認済みの主な装飾

| ブロック | 現在の確認済み範囲 |
|---|---|
| Group | 背景色、文字サイズ、枠線、角丸、margin、padding、layout・blockGapの非inline保持 |
| Paragraph | 背景色、文字色、リンク色、font family、fit text、枠線、margin、padding、確認済みtypography |
| Buttons / Button | 外側・内側・リンク要素、文字色、背景色、リンク色、文字サイズ、枠線幅、JSONだけの幅 |
| Quote | 背景色、角丸、各辺の枠線、左枠色、子Paragraphの確認済み装飾 |
| Pullquote | 背景色、枠線幅、角丸 |
| Accordion一式 | 親子構造、Headingの背景色・文字サイズ・枠線、toggle/title/icon要素 |
| Columns / Column | 親子構造、ルートタグと必須クラス。幅・gap・縦位置の装飾は未確認 |
| Separator | 既定の `has-alpha-channel-opacity`、`hr` / `div` のコア対応 |

### 4.3 Tableの現在位置

Tableには、WordPressで確認済みの正解例と、次の厳格なclass・タグ関係があります。

- `wp-block-table` は `figure`
- `has-fixed-layout` は `table`

ただし、Tableは現在の13ブロック用シリアライズ対応表には入っていません。したがって、Table全体のJSON・class・styleを双方向に完全照合する状態ではありません。

### 4.4 ListとHeadingの現在位置

List / List itemとHeadingは、構造、親子関係、ルートタグ、一部属性を検査できます。しかし、装飾JSONからclass/styleを生成・照合する13ブロックの対応表にはまだ入っていません。

## 5. class参考ファイルの意味

現在のclass参考ファイルには4,700クラスがあります。

| 分類 | 件数 | Linterでの扱い |
|---|---:|---|
| 厳格 | 19 | 確認済みタグ以外に付いた場合、警告候補になる |
| 参考 | 4,681 | 観測タグは参考情報。別タグでの使用を禁止しない |

厳格関係は、WordPressコアの保存処理を別途確認したものだけです。主な対象は次のとおりです。

- Tableの `wp-block-table`、`has-fixed-layout`
- Groupの `wp-block-group`
- Buttons / Buttonの三つの構造class
- Quote / Pullquoteのルートclass
- Accordion一式のルート・toggle・title・icon class
- Columns / Columnのルートclass
- Separatorの `wp-block-separator`、`has-alpha-channel-opacity`

一方、`has-background`、`has-text-color`、色slug、フォントfamilyなどは、多数のブロックやタグで使用される可能性があります。そのため、一つの保存例だけを根拠に特定タグ専用とは判定しません。

未知の独自classも、それだけを理由にエラーにはしません。

## 6. 診断レベルの考え方

### Errorに向くもの

- ブロックコメントの欠落・不一致
- 必須親ブロックの欠落
- 非コンテナブロック内部への子ブロック混入
- HTMLタグのWordPress境界越え
- ブロックのルートHTML形状が明確に違う
- Separator内部へのcode断片混入
- 壊れたブロックJSON

これらは、本文消失、ブロック無効化、構造崩壊につながる可能性が高い項目です。

### Warningに向くもの

- 確認済みJSONとclass/styleの不一致
- 厳格なclass・タグ関係の不一致
- 未知の属性や入力ミス候補
- 移植性上の注意

装飾不一致は、テーマ、WordPressバージョン、別の正しい保存形の影響を受ける可能性があるため、構造Errorと同じ扱いにはしません。

### 診断しないもの

- 対応表にない装飾
- 参考classの未観測タグでの使用
- 未知の独自classそのもの
- テーマCSSによる最終的な見た目

「未対応」を「間違い」と判定しないことが、誤検出を抑えるための重要な方針です。

## 7. 現在できないこと

### 7.1 Gutenberg完全互換検証

次は現在できません。

- Gutenbergの `save()` と同一のHTMLを全ブロックで生成する
- deprecated版を含む全ブロックバージョンを判定する
- WordPress更新ごとの保存形式差を自動追従する
- RichTextの空白、改行、selection、文字列正規化を完全再現する
- Dynamic BlockのPHP側出力を完全検証する
- ブロックサポートとStyle Engineを丸ごと再実装する

これらを完全に実装すると、Gutenbergの一部を別言語で再実装し、継続保守する規模になります。

### 7.2 テーマとプリセットの完全検証

次は保証しません。

- 指定した色slugやspacing slugが対象サイトの `theme.json` に存在するか
- テーマが生成する最終CSS
- テーマ独自classとブロックstyle variation
- Twenty Twenty-Five以外のテーマ差

JSONとHTMLが対応していても、そのテーマにプリセットがなければ期待した表示にならない可能性があります。

### 7.3 プラグイン・独自ブロック

- プラグイン独自ブロック
- テーマ独自ブロック
- サイト固有の拡張属性
- JavaScriptで追加されたブロックフィルター

これらは、現在のコアブロック辞書の対象外です。

### 7.4 内部IDとサイト固有データ

次は自動生成・自動修正の対象外です。

- Image、Video、Gallery等のメディアID
- 添付ファイルIDとURLの対応
- 内部ページリンクの `data-id`
- サイト固有URL
- WordPressメディアライブラリーとの紐付け

画像・動画は、正解コードを貼り付けた後にWordPress側でアップロードまたはライブラリー選択を行う現在の運用が安全です。

### 7.5 自動修正と「コアブロックチェック」画面

次は計画書にありますが、まだ実装されていません。

- 「コアブロックチェック」メニュー・ボタン
- 独立した候補ウインド
- JSON入力候補
- class入力候補
- style修正候補
- チェックした候補だけの自動挿入
- 変更前後のプレビュー
- 一回のUndoにまとめる編集
- 解析後に変更されたタブへの安全停止

現在のGrammar Checkは診断中心であり、記事を自動修正しません。

## 8. WordPressプレビューの位置付け

RegexPadには、簡易表示とTwenty Twenty-Five表示のローカルWordPressプレビューがあります。

プレビューで確認できるのは主に次です。

- 表示結果
- WordPressコアCSSを通した見た目
- Twenty Twenty-Fiveでのフロント側表示

プレビューだけでは、次を保証できません。

- Gutenbergコードエディターからビジュアルエディターへ切り替えたときのinvalid判定
- 保存後の再シリアライズ
- 保存・再読込・再編集でブロックが維持されること

したがって、プレビュー成功をGutenberg受入成功の代わりにはしません。

## 9. 現実的な日常運用

### 9.1 通常の記事本文

先生が現在使用している次の形は、人間が理解・修正しやすいという大きな利点があります。

```html
<!-- wp:paragraph -->
<p><strong style="...">文章</strong></p>
<!-- /wp:paragraph -->
```

色、背景、太字、下線などの文字単位装飾では、この方法を基本運用にするのは合理的です。

ただし、`strong` はインライン要素です。段落全体のmargin、padding、枠線、幅、レイアウトなどは、`p` ブロック全体への装飾と同じ意味にはなりません。また、WordPressが保持するRichTextの範囲も実際の保存・再編集で確認する必要があります。

### 9.2 段落全体やコンテナの複雑な装飾

次の場合は、WordPressの右パネルを使用し、保存された正解コードをそのまま基準にする方が安全です。

- 段落全体のmargin・padding
- 段落全体の枠線
- Group、Columns、Accordion等のレイアウト
- hover設定
- テーマプリセットを使用する色・spacing・font family

### 9.3 推奨する役割分担

| 作業 | 推奨手段 |
|---|---|
| 本文と単純な文字装飾 | RegexPadで読みやすいHTMLを編集 |
| 構造事故の確認 | RegexPadのGrammar Check（F7） |
| 複雑なコアブロック装飾 | WordPress右パネルで作成 |
| 見た目の確認 | RegexPadプレビューとWordPressフロント表示 |
| ブロック互換性の最終確認 | Gutenbergで保存・再読込・再編集 |

## 10. 今後の開発方針

### 維持する価値が高いもの

- 本文消失につながる構造Errorの精度向上
- 実際の壊れた例・正解例による回帰fixture
- 誤検出を増やさない辞書駆動ルール
- 問題行への移動と再チェック
- WordPressへ貼り付ける前の安全確認

### 無理に目指さないもの

- Gutenberg完全互換
- 全ブロック・全装飾の自動生成
- WordPress更新への完全自動追従
- 推測だけに基づく修正

### 対応表を追加する条件

新しいJSON・class・style対応は、次がそろった場合だけ追加します。

1. 実際のWordPressで保存された正解例
2. 可能なら壊れた例との比較
3. 症状と原因
4. 期待する診断
5. 正解例では対象診断が出ない回帰テスト
6. WordPressでの保存・再読込・再編集結果

これにより、対応表を増やしても未確認規則による誤警告を避けます。

## 11. Linterアルゴリズムを書き換える必要があるか

構造Linterを最初から全面的に書き換える必要はありません。

現在の実装はすでに、次を分けています。

- HTML構造検査
- WordPressブロック境界検査
- ブロック属性JSON検査
- 確認済みシリアライズ対応表による補助検査
- class参考情報と厳格関係

人間が巨大なJSONとHTMLを目視照合する代わりに、確認済み対応表をコンピューターが機械的に照合する構造はできています。

ただし、候補生成・自動挿入まで行う場合は、既存Linterへ直接書き足すのではなく、計画済みの独立した候補エンジンとして実装する必要があります。Linterは診断、候補エンジンは編集提案、Gutenbergは最終受入確認という分担を保ちます。

## 12. 現在地の評価

現在のRegexPad WordPress Linterは、次の状態です。

| 評価項目 | 現在地 |
|---|---|
| HTML構造チェック | 実用段階 |
| WordPressブロック境界チェック | 実用段階 |
| 本文消失リスク検出 | 主要パターンを実装済み |
| 親子構造チェック | 主要コンテナを実装済み |
| ブロック属性JSON | 23ブロックの選択属性を部分対応 |
| JSON・class・style照合 | 13ブロックの実証済み部分だけ対応 |
| class・タグ参考 | 4,700クラス、厳格19件 |
| Gutenberg完全互換 | 対応していない |
| 自動修正 | 対応していない |
| コアブロック候補ウインド | 計画のみ、未実装 |
| メディア内部ID | 対象外 |

この状態は失敗ではありません。対象を「Gutenberg完全再実装」から「記事を壊す危険を減らす貼り付け前安全検査」へ明確に限定すれば、すでに実用的な価値があります。

## 13. 関連ファイル

- `search/html_typo_lint.py`: HTML・WordPress構造Linter
- `dictionaries/lint_reference.json`: 既知タグ・属性・ブロック属性
- `dictionaries/standards/wordpress_block_schema.json`: 23ブロックの選択属性スキーマ
- `dictionaries/standards/wordpress_block_serialization_reference.json`: 13ブロックの確認済み対応表
- `dictionaries/standards/wordpress_class_tag_reference.json`: class・HTMLタグ参考情報
- `CORE_BLOCK_CHECK_IMPLEMENTATION_PLAN.md`: 未実装の候補ウインド・自動挿入計画
- `tests/test_html_typo_lint.py`: Linter回帰テスト
- `tests/test_gutenberg_content_loss_lint.py`: Gutenberg本文消失リスクの回帰テスト
- `SCRIPT_STEP.md`: 実装・検証・受入境界の記録
