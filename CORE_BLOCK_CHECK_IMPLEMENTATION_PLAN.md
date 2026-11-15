# コアブロックチェック実装計画

作成日: 2026-11-15  
対象プロジェクト: `D:\PC\Python\regex_pad_project`  
状態: 実装前の段階計画

## 1. 目的

WordPressコアブロック内のHTMLタグへ `style=""` 等を記述した後、Regex Padの「コアブロックチェック」から、次の3種類を独立ウインドに表示する。

1. コアブロック開始コメントへ追加するJSON候補
2. `style=""` を持つHTMLタグ等へ追加する `class=""` 候補
3. JSON・class・style・HTMLタグの不一致に対する修正候補

利用者が候補のチェックボックスを選び、「選択候補を挿入」を実行したときだけ本文を変更する。解析、候補表示、チェック操作だけでは本文を変更しない。

## 2. 完成時の基本フロー

```text
HTMLのstyle/classを編集
        ↓
「コアブロックチェック」を実行
        ↓
カーソル位置のコアブロックと子ブロックを構造解析
        ↓
確認済み対応表から候補を構成
        ↓
独立ウインドに3分類で表示
        ↓
利用者が候補をチェック
        ↓
変更前後のプレビューを確認
        ↓
元のタブへ1回のUndo単位で反映
        ↓
再解析して不一致が解消したか確認
```

## 3. 対象範囲と実装方針

### 3.1 初期対象

- `core/group`
- `core/paragraph`
- `core/buttons` / `core/button`
- `core/quote` / `core/pullquote`
- `core/accordion` / `core/accordion-item` / `core/accordion-heading` / `core/accordion-panel`
- 正解例が確認済みの `core/table` 関係
- 今後、壊れた例と正解例がそろったコアブロック

最初の操作対象は、カーソルが置かれている1個のコアブロックとする。親Group内にカーソルがある場合でも、カーソルがParagraph内ならParagraphを主対象にし、必要に応じて親Groupとの関係も表示する。

### 3.2 初期対象外

- `core/image`、`core/video`、Gallery等のメディアIDを必要とするブロック
- 内部ID、添付ファイルID、WordPressメディアライブラリーとの紐付け
- 正解保存データがまだないList、Columnsの自動修正
- プラグイン独自ブロック、テーマ独自ブロック
- WordPressサイトへの自動アップロードや直接保存
- 推測だけに基づくclass・JSON・styleの自動挿入

対象外ブロックを検出した場合は、編集せず「現在は候補生成対象外」と表示する。

### 3.3 証拠の扱い

- WordPressで保存・再読込・再編集できた正解例を自動挿入規則の根拠にする。
- 壊れた例と正解例を対にし、症状、原因、期待診断、WordPress確認結果を記録する。
- WordPressコアCSSや一般的な命名規則だけで候補を自動確定しない。
- CSSに存在するclassと、特定ブロックの保存HTMLへ実際に挿入されるclassを区別する。
- 未確認規則は参考情報として表示できても、初期状態ではチェック不可・自動挿入不可にする。

## 4. 独立ウインドの仕様

新規 `CoreBlockCheckDialog` はモードレスとし、既存の文法チェックや参考表と同様にエディターと並べて表示できるようにする。

### 4.1 ウインド上部

- 対象ファイル名または「無題」
- 対象ブロック名。例: `core/group`
- 対象ブロックの開始行・終了行
- 解析時刻ではなく、解析元ドキュメントの識別情報と更新状態
- 「再チェック」ボタン

### 4.2 1. コアブロックJSON入力候補

表示例:

```text
[ ] backgroundColor: "accent-2"
    根拠: background-colorのプリセット変数
    挿入先: wp:group 開始コメント

[ ] style.spacing.padding.top: "var:preset|spacing|20"
    根拠: padding-top:var(--wp--preset--spacing--20)
```

各候補は、JSONパス、候補値、元になったHTMLタグ・CSSプロパティ、根拠fixture、挿入位置を保持する。

### 4.3 2. class入力候補

表示例:

```text
[ ] has-accent-2-background-color
[ ] has-background
[ ] has-medium-font-size
```

候補ごとに対象HTMLタグを明示する。複数のタグがある場合、同じclass名でもタグごとに別候補として扱う。既に存在するclassは候補から除外し、文字参照の空白もデコードして重複判定する。

### 4.4 3. 修正候補

表示例:

```text
[ ] 空の style="" を削除
[ ] margin-top をJSONと一致する値へ変更
[ ] 不足している wp-block-group を追加
[ ] 誤ったタグにある has-fixed-layout を削除
```

1つの不一致に「JSONをHTMLへ合わせる」「HTMLをJSONへ合わせる」の両案がある場合は競合グループにする。同じ競合グループでは1案だけ選択できるようにし、相反する修正を同時適用しない。

### 4.5 ウインド下部

- 「安全な候補をすべて選択」
- 「選択解除」
- 「変更プレビュー」
- 「選択候補を挿入」
- 「閉じる」

すべての候補は初期状態を未チェックとする。自動挿入前には、対象範囲の変更前・変更後を確認できるプレビューを表示する。

## 5. 候補データモデル

UIより先に、候補を表すGUI非依存のモデルを作る。

候補が最低限保持する情報:

- 一意な候補ID
- 分類: `block_json`、`html_class`、`repair`
- 対象ブロック名
- 対象ブロックの入れ子パス
- 対象タグ名と開始位置
- JSONパスまたはHTML属性名
- 現在値
- 候補値
- 根拠となる対応表ルールとfixture
- `verified` / `advisory` / `unsupported` の証拠レベル
- 編集開始位置・終了位置・置換文字列
- 競合グループID
- 自動適用可能か
- 利用者向け説明キー

候補モデルは翻訳済み文章を保持せず、メッセージキーと値だけを保持する。日本語・英語への変換はDialog側で行う。

## 6. 対応JSONの拡張方針

既存の `dictionaries/standards/wordpress_block_serialization_reference.json` を、双方向の候補生成に使える形式へ段階的に拡張する。

必要な情報:

- ブロック名
- 対象ルートタグ・子タグ
- JSONパス
- CSSプロパティ
- JSONからCSS値への変換
- CSS値からJSON値への逆変換
- JSON属性から生成されるclassテンプレート
- class生成時に必要な補助class
- classを挿入するタグ
- JSONだけに保持され、HTMLへ直接出ない項目
- 禁止される空属性
- 正解fixtureと不正fixture
- 確認したWordPressバージョン・テーマ
- ルールの証拠レベル
- 自動挿入可否

例:

```json
{
  "block": "group",
  "json_path": "backgroundColor",
  "html_target": "root",
  "class_templates": [
    "has-{value}-background-color",
    "has-background"
  ],
  "evidence_level": "verified",
  "auto_insert": true
}
```

値変換はPythonへ個別にハードコードせず、名前付き変換として管理する。初期候補:

- `wordpress_preset_to_css_variable`
- `css_variable_to_wordpress_preset`
- `identity`
- `kebab_case_slug`

未知の変換名、必要フィールド不足、壊れた正規表現、証拠fixture不在は起動時またはテスト時に検出し、自動挿入規則として読み込まない。

## 7. 実装STEP

### STEP 0: 仕様fixtureと受け入れ条件の固定

変更候補:

- `tests/core_block_check_fixtures/`
- 対応表JSON
- 計画・検証文書

作業:

1. 現在のGroup正解2例と空style不正例を初期fixtureとして移管または参照する。
2. HTMLのstyleからJSONを補う例、JSONからclassを補う例、不一致修正例を分ける。
3. 各fixtureに「自動挿入してよい候補」と「表示だけにする候補」を明記する。
4. WordPressでの保存・再読込・再編集結果を記録する。

完了条件:

- 同じ入力から期待候補が一意に定義できる。
- 未確認のList、Button、Columns、Quote、メディア規則が混入していない。

### STEP 1: 対応表スキーマのバージョンアップ

変更候補:

- `dictionaries/standards/wordpress_block_serialization_reference.json`
- 新規のスキーマ読込・検証モジュール
- 対応表テスト

作業:

1. 双方向変換、対象タグ、証拠レベル、auto_insert、競合情報を追加する。
2. 既存Group・Paragraph規則を新形式へ移す。
3. 不正な辞書では編集機能を無効化し、Linter自体は安全に継続できるようにする。

完了条件:

- 正しい対応表を型付きオブジェクトとして読める。
- 壊れた対応表を本文無変更で拒否できる。
- 既存Linter結果が変わらない。

### STEP 2: WordPressブロック構造解析の共通化

変更候補:

- 新規 `editor/core_block_structure.py`
- `search/html_typo_lint.py`
- 構造解析テスト

作業:

1. 開始・終了コメント、自己終了ブロック、親子関係、本文範囲を解析する。
2. カーソル位置から最内側ブロックを取得する。
3. 各ブロック自身のルートHTMLと、子ブロックのHTMLを区別する。
4. Linter内部の必要部分を共通解析層へ安全に移し、Linterと候補機能で同じ構造認識を使う。

完了条件:

- 入れ子Group/Paragraphで正しい対象を返す。
- コメントが壊れている場合は候補を作らず、構造エラーだけを返す。
- 共通化前後で既存Linter回帰テストが同じ結果になる。

### STEP 3: HTMLタグ・属性の位置付き解析

変更候補:

- 新規 `editor/core_block_html_targets.py`
- HTML位置解析テスト

作業:

1. タグ名、開始・終了位置、`class`・`style` 属性値範囲を保持する。
2. 複数行属性、引用符、文字参照空白、属性順序を扱う。
3. 同名タグが複数ある場合も、候補を正しいタグへ結び付ける。
4. `<code>` やコメント内の見本HTMLを編集対象から除外する。

完了条件:

- 候補が行番号だけでなく正確な文字範囲を持つ。
- 解析だけでは本文、選択範囲、Undo履歴を変更しない。

### STEP 4: styleからJSON候補を作るエンジン

変更候補:

- 新規 `editor/core_block_candidate_engine.py`
- 候補モデル
- 候補生成テスト

作業:

1. 対象タグのstyleを既存CSS解析器で読む。
2. CSSプロパティから、確認済みのJSONパスを逆引きする。
3. `var(--wp--preset--spacing--20)` を `var:preset|spacing|20` へ戻す。
4. 既存JSONと同じ値なら候補を出さない。
5. 既存JSONと異なる値なら修正候補へ回す。
6. 複数のHTMLプロパティが1つのJSON構造へ入る場合は安全に統合する。

完了条件:

- Groupのmargin、padding、border、radiusから正しいJSON候補が出る。
- Paragraphの全辺・個別辺borderから正しいJSON候補が出る。
- 未登録CSSプロパティから推測候補を作らない。

### STEP 5: JSONからclass候補を作るエンジン

変更候補:

- `editor/core_block_candidate_engine.py`
- class候補テスト

作業:

1. `backgroundColor` からslug付き背景classと `has-background` を作る。
2. `fontSize` から `has-{slug}-font-size` を作る。
3. ブロックと対象タグが対応表に一致する場合だけ自動候補にする。
4. 既存classを空白・文字参照を正規化して重複排除する。
5. custom classは削除せず、対応表にないclassも自動的に誤りとしない。

完了条件:

- 確認済みGroup例から不足classだけを候補にできる。
- JSONなしでslug付きclassを創作しない。
- 別タグ用のstrict classを自動挿入しない。

### STEP 6: 不一致と修正候補の生成

変更候補:

- 新規 `editor/core_block_repair_candidates.py`
- 修正候補テスト

作業:

1. 空の `style=""` 削除候補を作る。
2. JSONとstyleの値不一致を検出する。
3. JSONとclassの不足・不一致を検出する。
4. strict classとHTMLタグの不一致を検出する。
5. JSON側修正とHTML側修正が両方可能な場合、競合候補として提示する。
6. 構造が壊れている場合は、局所修正で安全なものだけを有効にする。

完了条件:

- 正解fixtureでは修正候補0件になる。
- 不正fixtureでは対象診断と修正候補が出る。
- 無関係な警告が残っていても、対象候補の有無を対で検証できる。

### STEP 7: 編集計画とプレビュー

変更候補:

- 新規 `editor/core_block_edit_plan.py`
- 変更プレビュー部品
- 編集計画テスト

作業:

1. 選択候補を非重複の文字列編集へ変換する。
2. JSONの既存キーを不用意に並べ替えず、必要箇所だけ追加・置換する。
3. class属性がなければ追加し、あれば値だけを統合する。
4. style/classの引用符、周囲空白、改行を可能な限り維持する。
5. 編集を後方位置から適用し、位置ずれを防ぐ。
6. 変更前・変更後のプレビューを生成する。

完了条件:

- 同じ候補を2回適用しても2回目は変更なしになる。
- 競合・重複する編集計画は適用前に拒否される。
- プレビューと実際の適用結果が一致する。

### STEP 8: 独立ウインドの実装

変更候補:

- 新規 `dialogs/core_block_check_dialog.py`
- `resources/app_text_ja.json`
- `resources/app_text_en.json`
- Dialogテスト

作業:

1. 3分類の候補一覧とチェックボックスを実装する。
2. 根拠、対象タグ、現在値、候補値を展開表示できるようにする。
3. 競合グループでは1候補だけ選べるようにする。
4. 参考候補は表示できてもチェック不可にする。
5. 日本語・英語切替を開いたまま反映する。
6. エディター横に置けるモードレスウインドにする。

完了条件:

- チェック操作だけでは本文が変わらない。
- 3分類、対象ブロック、対象行、証拠レベルが判別できる。
- 長いJSONやclassでも操作ボタンが画面外へ隠れない。

### STEP 9: MainWindowへの「コアブロックチェック」追加

変更候補:

- `main.py`
- bilingual resource JSON
- MainWindowテスト

作業:

1. 検索メニューに「コアブロックチェック...」アクションを追加する。
2. 初期段階では既存ショートカットと衝突しないよう、ショートカットは付けないか別途確認する。
3. ウインドを開いた時点の元エディター、タブ、文書revision、対象範囲を保持する。
4. タブ切替、本文変更、元タブ終了時は適用を無効化し、「再チェック」を要求する。
5. 現在タブへ黙ってフォールバックしない。

完了条件:

- 候補は必ず解析元の文書へだけ適用される。
- 別タブへ誤挿入されない。
- 複数MainWindowでも対象ウインドを取り違えない。

### STEP 10: 選択候補の安全な自動挿入

変更候補:

- MainWindowの適用ハンドラ
- `editor/core_block_edit_plan.py`
- Undo・タブ安全性テスト

作業:

1. 適用直前に文書revisionと対象文字列を再確認する。
2. 解析後に本文が変わっていたら挿入せず再チェックを求める。
3. 全編集を `QTextCursor.beginEditBlock()` / `endEditBlock()` の1単位で適用する。
4. カーソル、選択範囲、スクロール位置を可能な限り復元する。
5. 適用後に候補を再計算し、残った不一致を表示する。

完了条件:

- Ctrl+Z 1回で自動挿入全体を戻せる。
- Ctrl+Yで同じ変更をやり直せる。
- 保存前、保存後、未保存タブで同じ安全条件になる。

### STEP 11: Linterとの役割分離と連携

変更候補:

- `search/html_typo_lint.py`
- 候補エンジン
- 文法チェックDialog連携

作業:

1. Linterは引き続き読取専用とし、自動修正を直接実行しない。
2. コアブロックチェックは、Linter診断を候補生成の補助情報として使う。
3. 診断行をクリックしたとき、対象ブロックチェックを開ける導線は初期機能安定後に検討する。
4. 同じ不一致をLinterと候補機能が異なるルールで判定しないよう共通対応表を使う。

完了条件:

- F7文法チェックの既存挙動が変わらない。
- 候補ウインドを閉じてもLinter結果や本文が変わらない。

### STEP 12: 対象ブロックの段階追加

追加順:

1. Group・Paragraph
2. Button / Buttons
3. Quote / Pullquote
4. Accordion一式
5. 正解データがあるTable
6. List
7. Columns / Column

各ブロックは、次を満たしてから自動挿入対象へ昇格する。

- 正解fixture
- 対応する不正fixture
- WordPress保存・再読込・再編集の確認
- JSON→HTMLとHTML→JSONの方向別テスト
- Linterで正解側に対象診断が出ないこと
- 自動挿入後の結果が正解fixtureと一致すること

メディア関連はこの順序へ含めない。

### STEP 13: パッケージング、説明書、実機確認

変更候補:

- `dictionaries/README.md`
- `README.md`
- `README_jp.md`
- `SCRIPT_STEP.md`
- PyInstaller収集テスト

作業:

1. 新規Pythonモジュール、Dialog、翻訳、JSONが配布物へ入ることを確認する。
2. 操作方法、候補の証拠レベル、対象外ブロックを説明する。
3. ソース版で物理GUIを確認する。
4. EXEを再ビルドした場合だけ、配布版で同じ確認を行う。
5. WordPressへ貼り付け、保存、再読込、再編集を行う。

完了条件:

- ソース確認、EXE確認、WordPress確認を混同せず個別に記録する。
- WordPressプレビュー表示だけをGutenberg保存互換の合格条件にしない。

## 8. テスト計画

### 8.1 GUI非依存テスト

- 対応表の構文・型・参照fixture
- ブロックの入れ子解析
- タグ・属性の文字位置
- style→JSON候補
- JSON→class候補
- 不一致・競合候補
- 編集計画と冪等性
- 解析中の本文非変更

### 8.2 Qtテスト

- 3分類の表示
- チェック状態と競合制御
- 未確認候補の無効化
- 再チェック
- タブ切替時の適用無効化
- 元タブ終了時の安全停止
- 1回のUndo/Redo
- 日本語・英語の動的切替

### 8.3 回帰テスト

- 既存HTML/WordPress Linter
- 文法チェック独立ウインド
- タグ挿入
- Paragraph挿入
- Schema Reference
- PyInstaller JSON収集
- 複数タブ・複数ウインド

### 8.4 WordPress手動テスト

各対象ブロックについて次を確認する。

1. Regex Padで候補を表示する。
2. 必要候補だけを選択して挿入する。
3. WordPressコードエディターへ貼り付ける。
4. ビジュアルエディターへ切り替える。
5. 保存する。
6. ページを再読込する。
7. 再度ビジュアル・コード編集へ切り替える。
8. 「無効なコンテンツ」やブロック回復表示が出ないことを確認する。
9. デスクトップとスマートフォン幅で表示を確認する。

## 9. 安全要件

- 解析だけでは本文を変更しない。
- 候補はすべて初期未選択とする。
- 適用対象は解析元のタブ・文書へ固定する。
- 文書が変化した場合は古い候補を適用しない。
- custom classや未知のJSONを勝手に削除しない。
- JSON全体や開始タグ全体を不必要に再整形しない。
- 競合編集を同時適用しない。
- 変更は1回のUndoで戻せるようにする。
- 辞書が壊れている場合は編集機能を安全停止する。
- 自動修正できない場合も、元本文を保持して理由を表示する。

## 10. 実装単位の推奨

この機能は大きいため、次の単位で分けて実装する。

1. STEP 0～3: 読取専用の構造解析
2. STEP 4～6: 読取専用の候補生成
3. STEP 7～9: プレビューと独立ウインド
4. STEP 10～11: 明示選択された候補の適用
5. STEP 12: ブロックごとの段階追加
6. STEP 13: 配布・GUI・WordPress受け入れ確認

各単位の終了時に、正解fixture、不正fixture、Linter回帰、Ruff、Pyrightを実行する。1つの段階が安定する前に次のブロック規則を大量追加しない。

## 11. 初回実装の到達点

初回リリースでは、Groupとその子Paragraphに限定して次を実現する。

- カーソル位置のブロック判定
- JSON候補表示
- class候補表示
- 空styleと確認済み不一致の修正候補表示
- チェックした候補だけの挿入
- 変更プレビュー
- 1回のUndo
- 解析後に変更されたタブへの安全停止

Button / Buttons、Quote / Pullquote、Accordion一式、Table以降は、初回機能が安定してから正解データ単位で追加する。

## 12. 現時点で未実装のもの

この文書作成時点では、次はまだ実装していない。

- 「コアブロックチェック」アクション
- 独立候補ウインド
- style→JSON候補エンジン
- JSON→class候補エンジン
- チェック候補の自動挿入
- 変更プレビュー
- 対応表スキーマの双方向化

現在実装済みなのは、確認済みGroup/Paragraph対応表と、それを使った読取専用Linter検査までである。
