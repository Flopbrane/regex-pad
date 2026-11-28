# Gutenberg ビジュアルエディターの検証・復旧・保存動作解析

調査日: 2026-10-24 / 方針: 正規プロジェクトの `CODE_ANALYSIS_POLICY.md`

## 1. 結論と調査対象バージョン

**「復旧を試みる」は、元ソースの誤字だけを修正する処理ではない。ブロック定義に従って抽出できた属性と子ブロックから、対象ブロックを再生成する。元HTML全体や通常文章の保存を保証しない。**

実際のWordPress編集画面で次の現象を再現し、ブラウザー表示だけでなく、編集状態・保存用本文・データベースの `post_content` を比較した。

|現象|結果|実験|
|---|---|---|
|誤ったHTMLタグを含む見出しを復旧すると普通の文章まで消える|再現。`ORDINARY_TEXT_KEEP` が空の `<h2>` になる。正常な後続段落は保持|case_009|
|復旧箇所より後ろの段落・見出しが失われる|再現。閉じブロックコメント欠落で後続が段落の子になり、復旧後の段落の `save()` が子を出力しない|case_007|
|後続の `<br>` が `<br />` に変わり、改行処理も変わる|再現。余分な閉じブロックコメント以降がClassicになり、`autop` が適用される|case_008|
|ソースの `\n` が半角スペースになる|再現。正常な段落を1文字編集するとその段落内で変わる。隣の未編集カスタムHTMLは保持|case_006|
|境界が正常な投稿で復旧しただけで全後続ブロックが変わる|今回の対照実験では再現せず|case_004|
|通常の無効段落をHTMLへ変換すると `wp:html` が必ず二重化する|再現せず。今回の変換では外側のparagraphコメントを含めずHTML化|case_002|
|既にネストした `wp:html` が必ずinvalidになる|この版では成立しない。親子ともvalidとして読み込まれる|case_001|

「コアブロック単位で変わる」という見方は結果と一致する。ただし、**ユーザーが意図したブロック範囲と、壊れたコメントからWordPressが読み取ったブロック範囲が一致するとは限らない。** また、本文を保存する段階では編集後の投稿本文全体が生成・送信される。

対象環境:

- 既存Previewの `wordpress.zip` から `wp-includes/version.php` を読み、WordPress **7.1.3** と確認。
- 既存のPlayground / PHP.wasmを使った、別のメモリー上のWordPress環境。PHP 8.3 / Twenty Twenty-Five。
- Node `24.22.1`、Playgroundの準備版 `3.1.60`。Gutenbergプラグインは追加していない。
- GutenbergはこのWordPressに同梱されたもの。独立したGutenbergプラグインのバージョン番号を推定していない。原本ZIP、同梱ファイルのSHA-256を保存。
- 実操作はChrome上のWordPress編集画面。初期のin-app browser観察後、キャンバス観察をChromeに統一。操作・保存はローカル実験用投稿だけ。
- 本番サイトには接続していない。利用者の実サーバーとバージョン・プラグイン・権限が同じことは未確認。

## 2. 解析資料と対象モジュール

`analysis_cases/` に入力、各段階の本文、ブロックツリー、データベース本文、差分、操作メモを保存した。

|ファイル|内容|
|---|---|
|`before.wp_html`|実験入力。投稿作成直後にDBと一致することを確認|
|`after_open.wp_html`|エディター読込後の `getEditedPostContent()`。DBの未加工値とは区別|
|`after_resolve.wp_html`|復旧・変換・対照編集直後の保存用本文。何を行ったかは各 `note.md` を参照|
|`after_save.wp_html`|下書き保存完了後の編集側本文|
|`after_*_database.wp_html`|同時点でPHP `get_post()` から直接読んだDB本文|
|`after_*_blocks.json`|同時点の `core/block-editor.getBlocks()`。属性・子・invalid情報を含む|
|`after_*_state.json`|dirty / saving / draft状態とPHP側 `parse_blocks()` の結果|
|`after_reload*`|再読み込みを実施したケースの確認資料|
|`after_php_block_hooks.wp_html`|独立PHP実験で確認した、読込時Block Hooks処理後の本文|
|`raw_parser_blocks.json`|同梱JSの未変更parserを直接実行した、属性抽出前のツリー|
|`diff_*.txt`|段階別と保存前後の差分|

解析用 `server.mjs` は既存の公式アーカイブとモジュールを読み、別メモリー環境を起動する。観察ページは別ウィンドウのWordPress公開APIからデータを読み取る外部コードで、Coreファイルにパッチを当てていない。WordPress標準UIの復旧・変換・Save draftボタンを実際に操作した。観察ページのCaptureボタンは編集状態を変更しない。

`sources/` は原本ZIPから取り出した未変更の参照コピー。以下の行番号はこのコピーに対するもの。GPLライセンスも同梱した。

|対象|主要箇所|
|---|---|
|`@wordpress/blocks`|`js/dist/blocks.js`: 属性取得、検証、deprecated、parse、serialize、rawHandler|
|`@wordpress/block-editor`|`js/dist/block-editor.js`: invalid警告、比較UI、置換、RichText出力|
|`@wordpress/editor`|`js/dist/editor.js`: 編集本文取得、savePost、autosave|
|`@wordpress/rich-text`|`js/dist/rich-text.js`: whitespace、originalHTML保持、編集後再生成|
|ブロック境界parser|`js/dist/block-serialization-default-parser.js` と `class-wp-block-parser.php`|
|ブロック定義|`js/dist/block-library.js` と11種類の `blocks/*/block.json`|
|PHPの読込・保存|`blocks.php`、REST posts controller、`post.php`、`kses.php`、`formatting.php`|

paragraph / heading / htmlのUI実験を中心とした。list / list-item / group / columns / column / image / separator / spacerは定義の参照コピーを保存したが、全属性・全deprecated経路の操作試験を網羅したわけではない。

## 3. parseの流れと、JSより前のPHP処理

```text
DB post_content
  → PHPの読込処理（Block Hooks等でcontent.rawも加工される場合がある）
  → ブロックコメントparser：raw block tree / innerContent / innerBlocks
  → block.jsonに従うHTMLからの属性抽出
  → validate / 組込補正 / deprecated migration
  → Gutenbergの編集状態
```

**DB本文とRESTの `content.raw` は、壊れた入力では同じとは限らない。** REST posts controllerの2179行付近は `insert_hooked_blocks_into_rest_response()` を呼び、`blocks.php:1537` の処理が `content.raw` にもBlock Hooksを適用する。

`apply_block_hooks_to_content_from_post_object()` は `blocks.php:1333` 付近で一時的な `core/post-content` コメントで投稿を囲み、処理後に外す。境界コメントが壊れていると、この一時ラッパーの解析にも影響する。

独立PHP実験で、case_003の閉じ忘れに終了コメントが補われること、case_008の余分な `<!-- /wp:html -->` が `<!-- /wp:post-content -->` として返ることを確認した。DBはこの時点では変わっていない。`php_read_pipeline.json` に入力・DB・この処理後の全文とツリーを保存した。

JS parserは `block-serialization-default-parser.js:54` 以降。ブロックをコメントで切り、開始でスタックへ積み、終了で取り出す。通常のHTMLタグだけで兄弟ブロックを決めているのではない。

- 開始ブロックのない終了コメントに遭遇すると、残り全体をFreeformとして追加して終了する分岐がある（118–121行）。case_008の後続全体のClassic化につながる。
- 閉じ忘れがあると、後続ブロックがその子として取り込まれる。ケースでは「兄弟の並べ替え」ではなく「親子関係の変化」だった。
- このparserの終了分岐は開始・終了のブロック名を比較せずスタックを取り出す。名前が違う閉じコメントでも安全とは限らない。未変更の同梱parserに対する直接実験でも確認した。
- ブロック境界のparserと、属性抽出時のブラウザーHTML解析は別工程。DOMだけからDB変更を判定していない。

## 4. validateの流れ

`blocks.js:5755` の `parseRawBlock()` はブロックを正規化し、型を調べ、子をparseし、属性を抽出する。その後、通常ブロックでは以下を行う。

1. `validateBlock()` で現在の `save()` 出力と元のブロックHTMLを比較。
2. 不一致ならカスタムclass・aria-label・anchor等の組込補正を試す。
3. deprecated定義でも検証し、適合する場合は移行する。
4. なおinvalidなら `__unstableBlockSource` と検証情報を保持する。

検証は全文の文字列完全一致だけではない。`blocks.js:4817` の `isEquivalentHTML()` はHTMLトークンを比較し、空白だけのトークンを読み飛ばすなどの同等性判定をする。属性順やclassの比較にも専用処理がある。

したがって、**Gutenbergのinvalid判定は一般的なHTML/CSS Linterとも、RegexPadの構造チェックとも同一ではない。** 正しいHTMLでも現在のブロックの `save()` と合わなければinvalidになり得る。一方、HTMLの問題がすべてinvalidになるわけでもない。

## 5. invalid判定と通常文章の消失

### 見出しのタグ不一致：case_009

見出しのcontent属性は `h1,h2,h3,h4,h5,h6` を対象に抽出する（`block-library.js:33139`）。そのブロック内が `<div>` だと、普通の文章が存在していても見出しのcontentとして取り出せない。

入力:

```html
<!-- wp:heading -->
<div class="wp-block-heading">ORDINARY_TEXT_KEEP
SECOND_LINE</div>
<!-- /wp:heading -->
```

「復旧を試みる」後、下書き保存して直接DBから読んだ結果:

```html
<!-- wp:heading -->
<h2 class="wp-block-heading"></h2>
<!-- /wp:heading -->
```

`ORDINARY_TEXT_KEEP` と `SECOND_LINE` は消えた。正常な後続の `TAIL_KEEP` は残った。再読み込み後も文章は戻らなかった。

これは文章を意図的に削除する専用処理ではなく、「定義に沿って抽出できなかった文章を、再生成したsave出力が含まない」結果。`style`・`class` の問題だけでも常に全文が消える、と一般化はできない。classを取り込む組込補正やdeprecated移行も存在する。

## 6. 「復旧を試みる」の処理

実装は `block-editor.js:21649` 付近。

```text
createBlock(block.name, block.attributes, block.innerBlocks)
  → replaceBlock(block.clientId, recoveredBlock)
```

同じ名前・抽出済み属性・子から新ブロックを作る。元の `originalContent` とinvalid時のraw source保持情報を新ブロックにそのまま渡す操作ではない。`replaceBlock()` は `replaceBlocks()` に進み、`REPLACE_BLOCKS` をdispatchする（16404–16432行）。

**「元HTML全文を壊さずに修正」ではなく、「現在の型で保存できるブロックを作り直す」操作。** 型で表現できないHTML、読み取れなかった本文、想定外の子構造がある場合に情報落ちが起こり得る。

case_004では境界が正常な無効段落を復旧し、欠けた `</strong>` が補われた。後続の正常段落とカスタムHTMLの `\n` / `<br>` は保持された。この対照から、「必ず次の全ブロックへ破壊的な処理を走らせる」という実装・結果にはなっていない。

## 7. 「解決」「HTMLへ変換」「ブロックへ変換」

|UI|処理|影響|
|---|---|---|
|Resolve / 解決|`setCompare(true)`|比較ダイアログを開く。これ自体が復旧の確定操作ではない|
|Attempt recovery / 復旧を試みる|同じ型を抽出済み属性から再生成|元HTML全体の保持保証なし|
|Convert to HTML / HTMLへ変換|`core/html` を作り、`innerContent` に `originalContent` を渡す|対象型が変わる。HTML文法修復や安全化を保証しない|
|Resolve内のConvert to Blocks|`rawHandler({HTML: block.originalContent})` の結果で置換|HTMLを再解釈。1ブロックが複数になる場合もある|

根拠: `block-editor.js:21613–21710`。比較ダイアログのCurrent側はHTML変換、After Conversion側はブロック変換に接続されている。

この版のHTML変換は `createBlock('core/html', {}, [], [block.originalContent])`。`serialize(block)` で元の外側コメントまで含める実装ではない。case_002では無効段落の内側HTMLを1つのHTMLブロックにし、隣接ブロックは保持した。`wp:html` 二重生成は起きなかった。

この分岐に「すでにcore/htmlなら変換しない」という型名の明示guardは見当たらない。ただしこの版では通常のcore/html読込自体をvalidにするため、通常入力から同じinvalid UI経由で繰り返しHTML変換する経路を確認できなかった。**guard不在だけで、二重生成が実際に起こると結論しない。**

## 8. serialize、改行、br表記

`blocks.js:3764` の `serialize()` は配列順に各ブロックを出力し、ブロック間を `\n\n` で連結する。この関数に全兄弟を並べ替える処理はない。

- 通常のvalidブロック: `getSaveContent()` → その型の `save()` → HTML出力。
- raw sourceを持つinvalidブロック: `serializeRawBlock()` による元構造保持の分岐がある。ただしtrimや連続改行の圧縮もあり、厳密なバイト保持保証と同一ではない。
- core/html: この版では `innerContent` と子ブロックを専用の `serializeInnerContent()` で出力する（3702行）。
- コメントとJSON属性はWordPress形式で生成される。

### `\n` → 半角スペース：case_006

RichTextの `collapseWhiteSpace()` は `rich-text.js:987` 以降にあり、テキストノード内の改行・TAB等をスペースにまとめる。`fromHTMLElement()` は正規化した内部値とともに `originalHTML` も保持する（852–858行）。`toHTMLString()` は未編集ならその元HTMLを使える（875行）。

一方、編集後の `handleChange` 経路は新しいRichTextData等を生成する（2739–2753行）。その結果、元ソースの見た目上の改行に戻る保証はなくなる。

実験入力の段落:

```html
<p>TAIL_A
TAIL_B<br>TAIL_C</p>
```

文末に `!` を1文字追加して保存:

```html
<p>TAIL_A TAIL_B<br>TAIL_C!</p>
```

同じ投稿の未編集HTMLブロック内の `TEST\nNEXT<br>END` は保持された。**改行の空白化は保存ボタンだけの一律置換ではなく、RichTextとして読み直し・編集・再生成する経路と元HTML保持の有無に関係する。** HTML上のソース改行と表示上の改行を区別する必要もある。

### `<br>` → `<br />`：case_008

余分な閉じコメントの後ろが `core/freeform` になると、`blocks.js:5709` の `normalizeRawBlock()` がJS版 `autop()` を実行する。

`autop.js:160` は `<br>` / `<br/>` を `<br />` へ変え、続く処理は改行を `<br />\n` へ変える。case_008では `TAIL_A\nTAIL_B<br>TAIL_C` が `TAIL_A<br />\nTAIL_B<br />TAIL_C` になった。

このケースでは後続のブロックコメントまでClassicのHTMLとして扱われ、コメントの周囲に `<p>` が追加された。変化は復旧前の編集stateで既に確認でき、復旧・保存でDBへ確定した。

なお、PHP版 `wpautop()` にも同様のbr整形がある（`formatting.php:577`）。しかし今回の保存前stateの書き換えはJSのFreeform/autop経路で説明できる。フロント表示のフィルターだけをDB変更の原因にしていない。また `element.js:854` のvoidタグ出力は `<br/>` 型であり、全ての `/` 付きbr表記を同じ処理へ帰属させていない。

## 9. 下書き保存、autosave、PHP側

`editor.js:7236` の `getEditedPostContent()` は編集recordのcontentやblocksから保存用本文を得る。`savePost()` は78853行以降でそれを取得し、`editPost({content})`、`saveEntityRecord()` へ渡す。`editor.preSavePost` 等の拡張hookも存在する。

REST posts controllerは1317行付近で受信contentを `post_content` に入れ、980行付近で `wp_update_post()` を呼ぶ。保存時のフィルター・権限によるKSES処理は別に存在する。今回の実験はローカル管理者のため、権限差・本番プラグインの保存フィルターを検証したものではない。

全ケースで、保存完了後の編集側本文と直接取得したDB本文を比較した。case_007とcase_009の本文消失、case_008のbr変更は、保存前の編集出力に既に現れ、その出力とDBが一致した。**今回のこれらの変化を、保存APIが突然本文を削除・置換したものと判断する必要はない。**

autosaveも同じ投稿編集・シリアライズ系に関係するが、今回実操作で確定・比較したのはSave draft。独立したautosaveタイミング・revision保存・ネットワーク失敗時復元は未試験。

## 10. wp:htmlネストの結果

case_001は最初から二重のHTMLコメントを持つ対照入力。ブロックツリーは親core/html → 子core/htmlで、単なるテキスト上の二重ラッパーではなかった。この版の `parseRawBlock()` はcore/htmlを `isValid = true` として返す（`blocks.js:5778`）。既存ネストの保持と、新規ネストの自動生成は区別した。

case_002の通常段落からのHTML変換では、外側HTMLコメントが1組作られ、元paragraphコメントは取り込まれなかった。

したがって、**利用者の実環境で「HTMLで解決」により新たに二重化した具体的な経路は、今回の入力からは確定していない。** 古いWordPress、プラグイン、未登録ブロックfallback、コメントを含んだoriginalContent等は追加調査候補であり、確認済み事実ではない。

既存RegexPadの `wordpress_html_contains_block_comment` は原稿の移植性・意図しない構造への注意として有用だが、「7.1.3が必ずinvalidにする規則」として説明してはいけない。

## 11. block orderと後続全体の破損

case_003ではparagraphの閉じブロックコメントだけを欠落させた。後続のparagraphとheadingがその子として読まれ、画面では最初の段落しか通常編集できなかった。最初の段落へ `!` を1文字追加して保存すると、子の文章が保存出力から落ちた。これは復旧操作なしの対照。

case_007は同じ閉じコメント欠落に `</strong>` 欠落を組み合わせ、invalid UIを出したケース。

```text
読込時:
paragraph (invalid)
  ├─ paragraph: TAIL_A / TAIL_B / TAIL_C
  └─ heading: TAIL_HEADING

「復旧を試みる」後の編集ツリー:
paragraph (valid) ← 子2個は内部stateには残る

保存用本文 / DB:
paragraphの自身の内容だけ ← TAIL_*がない

再読み込み:
paragraph (valid) ← 子もなくなる
```

`block-library.js:53278` のparagraph `save()` はpとcontentを出し、一般的なcontainerブロックのように `InnerBlocks.Content` を出していない。誤って子になった後続はこの出力に現れない。

case_008は別経路で、余分な終了コメント以降が1個のClassicとして扱われるため、後続全体の書式が変わった。どちらも「その位置以降の全兄弟を並べ替える」専用処理を前提にせず説明できる。今回のケースでは独立したsiblingの並び替えは確認していない。

## 12. RegexPad linterへ還元できる事項

今回は解析のみ。RegexPadの実装・辞書・警告文は変更していない。`linter_observations.json` に既存linterでの検出結果を記録する。

|WordPress挙動|リスク|RegexPadの事前チェックと扱い|
|---|---|---|
|閉じコメント欠落で後続が子になる|復旧・編集・保存時に後続本文が落ちる|既存のmissing closing block、parent/childチェックを優先。警告に「復旧前に境界を直す」「巻き込み範囲」を示す拡張候補|
|余分・異種の閉じコメントでparserの解釈が変わる|後続Classic化、autop、ブロック境界破損|既存unexpected/mismatched closingを重視。個数一致だけでは不足。名前と対応位置のスタック検証を維持|
|想定タグがないとcontent属性が空になる|普通の文章も復旧で消える|既存block HTML shape / heading levelとの不一致を、本文消失リスクに結び付ける説明候補|
|paragraphに想定外の子がある|内部stateにあってもserialize時に落ちる|paragraph内部の別wpブロックを重点検査。許可されたcontainerの子とは分ける|
|HTML変換はraw originalContentを別型へ移す|HTML文法問題は残る|HTML化で安全になったと判断しない。閉じ忘れ等のチェックを継続|
|RichText再生成で空白が正規化される|原稿のソース整形が変わる|通常は情報・案内。単独で構文Errorにしない|

再現例は、将来「壊れた入力 / 手修正した正常入力 / WordPressでの復旧結果」を比較する回帰fixtureへ転用できる。**復旧結果を自動的に正解fixtureと扱わない。** case_009の復旧結果はvalidでも文章が消えている。

## 13. 追加しないErrorルールと利用時の回避策

次の差だけでErrorを追加しない: 通常の空白正規化、属性順、CSS空白、許容class、ブラウザーDOMだけの補完、テーマの見た目、正常なdeprecated移行。`<br>` と `<br />` の表記差自体も、その背景にClassic化や構造破損がある場合と分ける。

実用上の回避手順:

1. 警告が出たら、復旧前の原稿をRegexPad側へ保持する。
2. コードエディター上で開始・終了のブロックコメントとHTMLタグを直す。特に後続が巻き込まれていないか確認する。
3. style・class・ブロックJSONの対応を確認する。複雑な自由HTMLをどのブロックへ置くかは原稿の意図に基づいて決める。
4. ビジュアルへ戻し、意図したブロック数・文章・順序が保たれたことを確認する。
5. 保存後にコード表示・再読込結果を元原稿と比較する。invalid警告が消えたことだけでは文章保持の証明にならない。

## 14. 未解決事項と検証範囲

- 利用者の実原稿で、style/class指定のどの誤りが、どのWordPress版・プラグイン・権限で全後続の変更に結び付いたかは未確定。今回の合成例と同一原因と断定していない。
- 「HTMLへ変換」から新規wp:html二重化へ至る実例は未再現。7.1.3での既存HTMLネスト受容と、旧版の挙動を混同しない。
- 11種類全ブロックの全deprecated・transform・テーマ・plugin組合せ、autosave/revision、未知ブロックは網羅していない。
- 既存Previewは通常表示用でHTTP書込を拒否する。本解析は本体へ編集機能を追加せず、独立したlocalhost実験サーバーを使用した。
- Core / Gutenberg / 既存Preview runtime / RegexPad本体のソースは変更していない。既存runtime全ファイルの前後SHA-256と、参照コピーとZIP内原本の一致は別途検証した。
- EXEの再ビルド・配布は行っていない。本番WordPressでの操作・投稿変更も行っていない。

再現手順、各ケースの実施操作、スクリプトの使い方、検証結果は `analysis_cases/README.md`、`note.md`、検証JSONを参照。現行の診断・修復の実装範囲は [開発計画・作業記録](SCRIPT_STEPS.md) に記載する。

最終検証結果:

- Gutenberg調査: UI実験9ケース、保存証拠・参照原本の照合79項目、JS parser直接実験5項目、独立PHP実験6項目が成功。
- 既存RegexPadの回帰確認: 作業側・正規側ともpytest **640 passed**、Ruff成功、Pyright **0 errors / 0 warnings / 0 informations**。
- 正規側のresource / dictionary / analysis JSON **109ファイル**を解析できることを確認。
- 既存Preview runtime **2,281ファイル変更なし**。参照コピー29ファイルはZIP原本とバイト一致。分析に使ったサーバーの停止・接続不能も確認。
- `D:\PC\Python\regex_pad_project` へ解析資料と記録だけを反映し、manifest内 **263ファイル**のSHA-256一致を確認。正規側の既存 `.gitignore` 変更と方針書原本を保持。

外部の補助資料は [WordPress公式のブロックエラー解説](https://wordpress.org/documentation/article/block-error-unexpected-or-invalid-content/) と [Edit and Save API](https://developer.wordpress.org/block-editor/reference-guides/block-api/block-edit-save/)。版ごとにUI・保存形式が変わるため、本報告の個別結論はローカルに固定した7.1.3のソースと実験を根拠とした。
