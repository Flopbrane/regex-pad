# RegexPad 疑似マクロ・アーキテクチャ

XMLライクJSONエディターのGUI配置、ファイル責務、Signal、読込・保存フローは`MACRO_XML_LIKE_EDITOR_GUI_DESIGN.md`を基準とする。

更新日: 2026-11-18  
状態: 設計確定・段階実装中

## 1. 目的

疑似マクロは、RegexPadの既存検索・置換機能を利用し、複数の手順を上から順番に実行する機能である。

単なる連続置換ではなく、次の安全境界を設ける。

- JSONを読み込んだ未検証の`dict`をRunnerへ渡さない。
- 検索文字列・除外文字列・置換文字列をNormalizerが黙って変更しない。
- 読み込み時、GUI編集後、保存前、実行前に同じ検証規則を使用する。
- 全手順をメモリ上で処理し、プレビュー承認後に本文へ一度だけ反映する。
- ファイル形式、編集用モデル、実行用モデル、本文変換、文書保存を分離する。

## 2. 用語

### JSON Loader

JSONファイルをUTF-8で読み、JSON構文、重複キー、読み込み失敗を確認して、生の`object`または`dict`を返す。

疑似マクロ固有のキーや正規表現の意味は判断しない。

### Parser

Parserは文字列や構造を解析する部品であり、Managerではない。

初版ではJSON LoaderがJSON解析を担当できるため、`macro_parser.py`の具体的な役割は未確定である。行・列情報や重複キー位置など、Loaderだけでは不足する解析が明確になった場合に実装する。ファイルが存在することを理由に、無理に処理経路へ組み込まない。

### Bridge

Bridgeはデータ形式の変換だけを担当する小さな部品とする。

```text
dict ⇔ MacroJsonData
GUI用dataclass ⇔ MacroJsonData
```

Bridgeは正規表現検証、Unicode正規化、本文置換、保存、GUI表示を担当しない。

### Normalizer

省略可能な値、旧形式、内部表現を安全に統一する。

次の値は自動変更しない。

- 検索文字列
- 除外文字列
- 置換文字列
- バックスラッシュ
- 改行
- 全角・半角

### Validator

疑似マクロとして実行可能かを意味的に検証する。

- 正規表現と除外正規表現
- Unicode正規化形式
- Unicode正規化と置換文字列の関係
- 空の検索文字列
- 手順名の重複
- 後方参照
- ゼロ幅一致

dataclassへ変換可能かという構造型の確認と、実行可能かという意味検証を区別する。

### Linter

Loader、Bridge、Normalizer、Validator、Dry-runが返した診断を、利用者向けの`Error`、`Warning`、`Information`として表示する。

Linterは本文やマクロ定義を変更しない。

### MacroManager

疑似マクロ機能の窓口であり、各部品を正しい順序で呼び出す。

Manager自身はJSON変換、正規表現検証、検索・置換を実装しない。

### MacroRunner

検証済み手順を上から順番に処理し、既存の`SearchEngine`を駆動する。

```text
MacroManager
  ↓
MacroRunner
  ↓
SearchEngine
```

Runnerはファイルを保存しない。Runnerの出力は、変換後本文と手順別結果を含む実行結果である。

### Preview

本文を変更する前に、各手順の検索件数、除外件数、置換件数、最終結果を表示する。

### Saver

Macro Saverは疑似マクロJSONを保存する。変換後の記事本文は、既存のRegexPad文書保存機能が保存する。両者を混同しない。

## 3. データモデルの境界

### ファイル・編集用モデル

`MacroJsonData`と`MacroJsonStepData`は、`macro_format_v1.json`に対応する。setterを備え、XMLライクエディターから編集できるモデルである。

```text
MacroJsonData
├─ format_version
├─ macro_name
├─ description
└─ steps: tuple[MacroJsonStepData, ...]
```

setterはPythonの構造型に加え、既存の`NormalizationForm` Literalで定義された`NFC`、`NFD`、`NFKC`、`NFKD`または`None`だけを保証する。正規表現や項目間の排他条件はValidatorの責務である。

GUIでは、`NormalizationForm`のように許可文字列が規定されている値を自由入力させない。編集不可のドロップダウンを使用し、表示名とは別の内部値として`None`、`NFC`、`NFD`、`NFKC`、`NFKD`をGUI Bridgeへ渡す。今後追加される`Literal`や`Enum`項目も同じ選択方式とし、人間のタイプミスによる`ValueError`を入力時点で防ぐ。Validatorとsetterは、直接編集されたJSONやプログラム経由の入力に対する防御として残す。

Boolean項目もチェックボックスではなく、編集不可のドロップダウンから選択する。表示は項目に合わせて「無効／有効」「使用しない／使用する」「追加しない／追加する」とし、GUI Bridgeへは`currentData()`から得たPythonの`False`／`True`を渡す。文字列の`"true"`／`"false"`や整数の`0`／`1`へ変換しない。

丸数字のUnicode正規化後に`.`を付ける設定は、既存の検索・置換機能と同じ`append_dot_to_circled_number: bool`を使用する。JSONキーは`丸数字変換後ピリオド追加`とする。この値が有効になる条件（Unicode正規化が有効で、形式がNFKCまたはNFKDであること）はValidatorが確認する。

### 将来の実行用モデル

Validator通過後にRunnerへ渡す実行用モデルは、将来`frozen=True`のdataclassとして分離する。

```text
編集可能なMacroJsonData
  ↓ Normalizer / Validator / Compiler
変更不能な実行用モデル
  ↓
MacroRunner
```

これにより、検証後にGUIや別処理が値を書き換えることを防止する。

## 4. 共通準備経路

入力元がJSONでもGUIでも、実行前には同じ準備経路を通す。

```text
入力元
  ↓
Bridge
  ↓
MacroJsonData
  ↓
Normalizer
  ↓
Validator
  ↓
実行準備済みモデル
```

NormalizerとValidatorは、直接編集されたJSONに対する任意の保険ではなく、読み込み・保存・実行境界で必ず通す処理とする。

将来、重複呼び出しを防ぐ必要が生じた場合は、Bridgeを拡張せず、小さなPreparation ServiceまたはMacroManagerの調整処理で順序を統一する。

## 5. 新規マクロ入力経路

### 実行

```text
XMLライクエディター
  ↓
GUI Bridge
  ├─ ValueError: 入力値を保持してGUIへ戻す
  │              診断表示・対象項目を強調・フォーカス
  │              再入力を促し、保存しない
  │
  └─ 変換成功
  ↓
MacroJsonData
  ↓
MacroManager
  ├─ Normalizer
  ├─ Validator
  └─ MacroRunner
       ↓
       SearchEngine
       ↓
       Preview
```

### 保存

```text
XMLライクエディター
  ↓
GUI Bridge
  ├─ ValueError: 入力値を保持してGUIへ戻し、再入力を促す
  └─ 変換成功
  ↓
MacroJsonData
  ↓
Normalizer
  ↓
Validator
  ├─ Errorあり: 保存しない
  └─ Errorなし
       ↓
       File Bridge.to_dict()
       ↓
       JSON Saver
```

エディター入力後の`ValueError`は、Controllerが修正可能な入力診断へ変換する。入力文字列を消したり前回の正常値へ黙って戻したりせず、該当手順と入力項目へフォーカスを戻して再入力を促す。変換に成功するまで保存用モデルは更新せず、Runnerにも渡さない。入力項目へ対応付けられない`ValueError`だけを想定外例外としてLoggerへ記録する。

## 6. JSON読み込み・実行経路

```text
JSON Loader
  ↓
dict
  ↓
File Bridge.from_dict()
  ↓
MacroJsonData
  ↓
MacroManager
  ├─ Normalizer
  ├─ Validator
  └─ MacroRunner
       ↓
       SearchEngine
       ↓
       Preview
```

読み込み時のJSON構文エラー、重複キー、型変換失敗、意味検証エラーのいずれかがある場合はRunnerへ渡さない。

## 7. 既存マクロ編集経路

### 読み込みから編集画面まで

```text
JSON Loader
  ↓
dict
  ↓
File Bridge.from_dict()
  ↓
MacroJsonData
  ↓
Normalizer
  ↓
Validator
  ↓
GUI Bridge
  ↓
XMLライクエディター
```

読み込み時にWarningがある場合は編集画面へ表示できるが、Errorがあるデータを実行用モデルとして扱わない。

### 編集後の保存

```text
XMLライクエディター
  ↓
GUI Bridge
  ├─ ValueError: 入力値を保持してGUIへ戻し、再入力を促す
  └─ 変換成功
  ↓
MacroJsonData
  ↓
Normalizer
  ↓
Validator
  ├─ Errorあり: 保存しない
  └─ Errorなし
       ↓
       File Bridge.to_dict()
       ↓
       JSON Saver
```

## 8. 本文変換経路

マクロ定義の保存経路と、記事本文の保存経路を分ける。

```text
検証済みマクロ
  ＋
元の本文スナップショット
  ↓
MacroRunner
  ↓
手順1の結果
  ↓
手順2の結果
  ↓
手順Nの結果
  ↓
MacroRunResult
  ↓
Preview
  ↓ 承認
エディターへ一度だけ反映
  ↓
既存のUndo / 文書保存機能
```

各手順の出力を次の手順の入力とする。途中で失敗した場合は、元の本文へ部分的な変更を残さない。

## 9. JSON Version 1の基準

基準ファイルは`macro/macro_format_v1.json`とする。

```text
形式バージョン
マクロ名
説明
手順[]
  ├─ 手順名
  ├─ 有効
  ├─ 正規表現
  ├─ Unicode正規化
  ├─ Unicode正規化形式
  ├─ 丸数字変換後ピリオド追加
  ├─ 検索文字列
  ├─ 除外文字列
  └─ 置換文字列
```

`null`と空文字列を区別する。

- `置換文字列: null`: Unicode正規化などにより置換文字列を使用しない。
- `置換文字列: ""`: 一致部分を削除する。
- `除外文字列: null`: 除外条件を使用しない。

## 10. Bridgeの責務

### File Bridge

```text
dict ⇔ MacroJsonData
```

- 日本語JSONキーと英語property名の対応
- 配列と手順tupleの対応
- dataclassへ変換可能な構造型の確認
- `null`と`None`の対応

### GUI Bridge

```text
GUI用dataclass ⇔ MacroJsonData
```

XMLライクエディターの入力部品とファイル用モデルを分離する必要が生じた段階で追加する。

### Bridgeが担当しないもの

- 正規表現コンパイル
- Unicode正規化
- 排他条件検証
- 検索・置換
- プレビュー生成
- ファイル読み書き
- GUI表示

## 11. MacroManagerの責務

MacroManagerは、CUI・GUI・ファイル読込の共通窓口になる。

予定する利用単位は次のとおりである。

```text
load_macro
validate_macro
preview_macro
execute_macro
save_macro
```

ただし、各機能のロジックはLoader、Bridge、Normalizer、Validator、Runner、Saverへ委譲する。Managerを巨大な処理クラスにしない。

## 12. 推奨実装順序

1. File Bridge (`dict ⇔ MacroJsonData`)
2. Normalizerの安全な変換規則
3. Validatorの意味検証
4. 診断モデルとLinter表示
5. MacroManager
6. MacroRunnerと既存SearchEngine接続
7. Dry-runとPreview
8. JSON Loader / Saverの不足分
9. GUI用dataclassとGUI Bridge
10. XMLライクエディター

File Bridgeは、既に確定した`MacroJsonData`のproperty名を基準にでき、Loaderなしでも辞書fixtureから単体テストできるため、次に実装しやすい部品である。

## 13. 現在の実装状況

### 実装済み

- `macro`パッケージの骨組み
- `macro_format_v1.json`
- `MacroJsonStepData`
- `MacroJsonData`
- 全property getter/setter
- setterでの構造型確認
- 丸数字変換後ピリオド追加のBoolean property
- 手順のtuple保持
- JSONデータモデルの集中テスト
- File Bridge（`dict ↔ MacroJsonData`）
- UTF-8 JSON Loader（重複キー検出を含む）
- 原子的なUTF-8 JSON Saver
- `app_base_dir()/macro`の既定保存場所と変更可能な保存フォルダ
- 文字列を変更しないVersion 1 Normalizer
- Error／Warning／Information診断モデル
- Version 1の意味規則と正規表現を検査するValidator

### 未実装

- GUI Bridge
- Linterの翻訳・GUI表示
- MacroManager
- Runner
- Preview
- 実行用の変更不能dataclass
- XMLライクエディター
- GUI接続
- 疑似マクロ実行

## 14. 非目標と安全方針

- JSONを実行可能なPythonコードとして評価しない。
- 読み込み時に検索文字列や正規表現を自動修正しない。
- Validator Errorがある定義をRunnerへ渡さない。
- マクロ実行中に本文へ段階的な変更を反映しない。
- 既存の検索・置換エンジンを複製しない。
- Macro Saverと記事本文Saverを混同しない。
- ParserをManagerの別名として扱わない。

この文書を疑似マクロ設計の基準とし、後続実装で設計を変更する場合は、先にこの文書と作業記録を更新する。


## 15. Structured editor implementation (2026-11-20)

This status supersedes the earlier unimplemented GUI/GUI Bridge list. The XML-like editor is now available from Macro > Pseudo-macro editor. It edits Version 1 JSON through an independent modeless window; it does not execute macros or modify article text.

- `macro/editor_data_model.py`, `editor_bridge.py`, and `editor_session.py` separate editable state from file models and preserve nullable strings.
- `dialogs/macro_step_editor_widget.py`, `macro_diagnostic_table.py`, and `macro_editor_window.py` provide the form, XML-like outline, step operations and diagnostic navigation.
- `dialogs/macro_editor_controller.py` coordinates existing Loader, Normalizer, Validator and atomic Saver, debounced diagnostics, JSON preview and Save/Discard/Cancel handling.
- Closed values use non-editable ComboBoxes with typed item data. Normalization and regular-expression use remain independent. Unicode normalization disables replacement and writes null; an empty enabled replacement writes an empty string.
- Input-derived `MacroEditorInputError` includes the step/field and returns focus to that input. Unexpected validation exceptions are logged and block saving. File failures preserve the current document and dirty state.
- MainWindow keeps one editor per main window and checks unsaved macro changes before closing. Local settings retain the macro folder, editor geometry and horizontal splitter state. Japanese and English UI text is included.
- MacroManager, Runner, execution preview, article application, XML import/export and document-wide Undo/Redo remain future work. EXE rebuilding and physical Windows GUI acceptance are separate from source validation.


## 16. Manager and execution implementation (2026-11-20)

This section supersedes the previous deferred Manager/Runner/Preview and execution status. The editor now provides Run preview, followed by explicit Apply to document or Cancel.

- MacroParser is the shared JSON text parsing boundary, including duplicate-key rejection. MacroJsonLoader performs UTF-8 file I/O and delegates parsing; no parallel JSON parsing path was added.
- MacroCompiler normalizes and validates file models, then creates frozen MacroDefinition/MacroStep tuples with frozen SearchOptions. GUI edits cannot alter an in-progress run.
- MacroManager exposes prepare_macro, load_macro, validate_macro, save_macro, execute_macro and preview_macro. It delegates parsing, validation, running and atomic JSON saving. Its execute operation returns an in-memory result and never writes an article or a file.
- MacroRunner applies each enabled step to the previous step's output through the existing SearchEngine. Reports include candidate matches, exclusions and replacements per completed step. Disabled steps have zero counts. MacroLinter combines static and runtime diagnostics, including no eligible matches.
- Regex replacement templates are validated even when there are no matches. Zero-width searches on the empty string are rejected before saving/execution; context-dependent zero-width matches are rejected on each step's actual input. Any failed run returns the original text, with no partial result eligible for application.
- Version 1 has no case-sensitivity field: execution follows the existing SearchOptions defaults (case insensitive; regex MULTILINE; no whole-word or selection-only restriction). A run covers the complete active document. Explicit inline regex flags remain supported. Null/empty strings and regex text are never normalized by the preparation boundary.
- SearchEngine now exposes analyze_matches and validate_replacement, so macro code does not duplicate search/replacement logic. Literal replacement backslashes are escaped before passing to Python re.sub, preventing literal Windows paths or backreference-like text from being interpreted as regex replacements. This also corrects the same literal replacement behavior in normal search/replace.
- MacroRunPreviewDialog displays source/output, step counts and diagnostics. The output fields are read-only. Error, unchanged and all-disabled results cannot be applied. MacroExecutionController binds approval to the original editor, QTextDocument, revision and text; closed/moved targets, another active tab, changed text/revision or read-only state block application.
- Approval applies the exact reviewed output without rerunning the macro, using one QTextCursor edit block. Existing Undo/Redo and normal article saving remain in charge afterward. Cancelling a preview changes neither text nor Undo state.
- Logger records unexpected execution exceptions at the GUI boundary; ordinary validation and dry-run diagnostics stay in the diagnostic UI.

Source implementation and canonical verification are recorded in SCRIPT_STEP.md Step15-section74. XML import/export, drag-and-drop ordering and document-wide macro-definition Undo remain outside this Version 1 implementation. Packaged EXE rebuilding and physical Windows GUI acceptance are separate checks.
