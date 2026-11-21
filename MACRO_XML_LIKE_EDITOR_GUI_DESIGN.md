# 疑似マクロ XMLライクJSONエディター GUI設計

更新日: 2026-11-19  
状態: GUI実装前の基準設計

## 1. 目的

疑似マクロJSONを、利用者がJSON構文やエスケープ規則を直接意識せず編集できる独立ウインドウを追加する。

「XMLライク」は保存形式をXMLへ変更する意味ではない。左側に次のような階層アウトラインを表示し、右側のフォームで値を編集するUI表現を指す。

```text
<macro name="WordPress本文整形">
  <step name="insert_@@@" enabled="true" />
  <step name="normalize_fullwidth_alphanumeric" enabled="true" />
</macro>
```

永続化形式は引き続きVersion 1のJSONとする。

```text
GUI
  ⇅ GUI Bridge
MacroJsonData
  ⇅ File Bridge
dict
  ⇅ Loader / Saver
JSONファイル
```

## 2. 基本方針

- 独立したモデルレスウインドウとして表示する。
- XML文字列を生成・解析する機能は作らない。
- JSONキーを利用者へ直接入力させない。
- 手順の追加、複製、削除、並べ替えをGUIで行う。
- 検索・除外・置換文字列をNormalizerで変更しない。
- `null`と空文字列をGUI上でも区別する。
- 許可文字列が規定されている項目は自由入力にせず、編集不可のドロップダウンから選択する。
- Errorが存在する場合は保存・実行へ進めない。
- Warningは表示するが、保存を禁止しない。
- Loader、Saver、Normalizer、Validatorの例外や診断をGUI層で握り潰さない。
- エディター入力から発生した`ValueError`はGUIへ戻し、該当項目の再入力を促す。
- LoggerはController境界で記録し、処理結果の代わりにしない。
- 本文変換機能とマクロ定義ファイルの編集を混同しない。

## 3. ウインドウ種別

`MacroEditorWindow`は`QMainWindow`を使用する。

理由:

- ツールバー、ステータスバー、中央Splitterを自然に配置できる。
- Regex-Pad本文エディターとは別に開いたまま操作できる。
- 将来、複数マクロファイルやJSONプレビュー用Dockを追加できる。
- 大型の編集画面を`QDialog`へ詰め込まずに済む。

MainWindowは`MacroEditorWindow`への参照を1個保持する。既に開いている場合は新規作成せず、既存ウインドウを前面へ移動する。

## 4. GUI全体配置

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ 疑似マクロエディター - my_macro.json                                      │
├────────────────────────────────────────────────────────────────────────────┤
│ [新規] [開く] [保存] [名前を付けて保存]  [検証]  [JSON確認]  [閉じる]     │
├────────────────────────────────────────────────────────────────────────────┤
│ 保存先: D:\...\macro\my_macro.json                         [フォルダ設定] │
├────────────────────────────────────────────────────────────────────────────┤
│ 形式バージョン [1: 読取専用]   マクロ名 [______________________________] │
│ 説明             [______________________________________________________] │
├───────────────────────────────┬────────────────────────────────────────────┤
│ XMLライク・アウトライン       │ 選択した手順の編集                         │
│                               │                                            │
│ ▼ <macro>                     │ 手順名       [__________________________] │
│   ├ <step insert_@@@>         │ 有効             [有効 ▼]                  │
│   ├ <step normalize...>       │ 正規表現         [使用する ▼]             │
│   └ <step ...>                │ Unicode正規化    [使用しない ▼]           │
│                               │ 形式 [NFKC ▼]  「.」追加 [追加しない ▼]   │
│ [追加][複製][削除]            │                                            │
│ [上へ][下へ]                  │ 検索文字列                                 │
│                               │ ┌────────────────────────────────────────┐ │
│                               │ │                                        │ │
│                               │ └────────────────────────────────────────┘ │
│                               │ 除外文字列 [使用する ▼]                   │
│                               │ ┌────────────────────────────────────────┐ │
│                               │ │                                        │ │
│                               │ └────────────────────────────────────────┘ │
│                               │ 置換文字列 [使用する ▼]                   │
│                               │ ┌────────────────────────────────────────┐ │
│                               │ │                                        │ │
│                               │ └────────────────────────────────────────┘ │
├───────────────────────────────┴────────────────────────────────────────────┤
│ 診断                                                                       │
│ [Error] 手順2 / 検索文字列 / 正規表現が不正です                           │
│ [Warning] 有効な手順がありません                                          │
├────────────────────────────────────────────────────────────────────────────┤
│ 2手順 | Error 1 / Warning 1 | 未保存                                      │
└────────────────────────────────────────────────────────────────────────────┘
```

## 5. サイズ方針

- 初期サイズ: `1050 x 760`程度。
- 最小サイズ: `760 x 560`程度。
- 画面解像度を超える固定最小高さを指定しない。
- 中央部は横方向`QSplitter`とする。
- 左ペイン初期比率30%、右ペイン70%。
- 診断領域は縦方向`QSplitter`または折りたたみ可能な下部パネルとする。
- 前回のウインドウ位置・サイズ・Splitter比率は、GUI実装の最終段階でローカル設定へ保存する。

## 6. 左ペイン: XMLライク・アウトライン

### 使用Widget

`QTreeWidget`を使用する。

Phase 1では次の2階層だけを表示する。

```text
<macro name="...">
  <step name="..." enabled="true" />
  <step name="..." enabled="false" />
</macro>
```

各プロパティを子ノードとして大量に表示しない。プロパティ編集は右ペインへ集約する。

### 表示規則

- ルート: `<macro name="マクロ名">`
- 有効な手順: `<step name="手順名" enabled="true" />`
- 無効な手順: `<step name="手順名" enabled="false" />`
- Errorのある手順: 赤色アイコン。
- Warningのある手順: 黄色アイコン。
- 編集済み手順: `*`または編集済みアイコン。
- 手順名が空の場合: `<step name="(未設定)" ... />`

### 操作

- 追加: 現在位置の次へ新しい手順を追加する。
- 複製: 選択手順を完全コピーし、手順名末尾へ`_copy`を付ける。
- 削除: 確認後に選択手順を削除する。
- 上へ／下へ: `steps`の順序を変更する。
- 選択変更: 右ペインへ対象手順を表示する。
- ドラッグ並べ替えはPhase 2。Phase 1では上へ／下へボタンだけにする。

## 7. 右ペイン: 手順編集フォーム

### 基本Widget

- 全体: `QScrollArea`
- 配置: `QFormLayout`と小さな`QGridLayout`
- 手順名: `QLineEdit`
- 有効: 編集不可のBoolean `QComboBox`
- 正規表現: 編集不可のBoolean `QComboBox`
- Unicode正規化: 編集不可のBoolean `QComboBox`
- 正規化形式: 編集不可の`QComboBox` (`未指定`, `NFC`, `NFD`, `NFKC`, `NFKD`)
- 丸数字ピリオド追加: 編集不可のBoolean `QComboBox`
- 検索・除外・置換: 既存`RegexInputEdit`

正規表現とUnicode正規化は、それぞれ独立したBoolean ComboBoxとし、排他的な選択にはしない。基準JSONでは、正規表現で対象を選び、Unicode正規化で一致文字列を変換する組み合わせが存在する。

### 規定値のドロップダウン方針

`Literal`、`Enum`、仕様上の固定候補など、許可文字列があらかじめ決まっている項目には、自由入力できない`QComboBox`を使用する。`setEditable(False)`を明示し、キー入力による未知の値を作成できないようにする。

Unicode正規化形式の候補は次のとおりとする。

| GUI表示 | `currentData()`で得る内部値 |
| --- | --- |
| 未指定 | `None` |
| NFC | `"NFC"` |
| NFD | `"NFD"` |
| NFKC | `"NFKC"` |
| NFKD | `"NFKD"` |

表示文字列と保存値を分離し、モデルへ渡す値には`currentText()`ではなく`currentData()`を使用する。これにより、「未指定」の翻訳や将来の表示名変更がJSON値へ混入しない。

Booleanもチェックボックスや自由入力ではなく、編集不可の`QComboBox`で選択する。表示文言は項目の意味に合わせてもよいが、内部値は必ずPythonの`bool`とする。

| 用途 | GUI表示例 | `currentData()`の内部値 |
| --- | --- | --- |
| 手順の有効状態 | 無効 / 有効 | `False` / `True` |
| 機能の使用状態 | 使用しない / 使用する | `False` / `True` |
| 文字の追加状態 | 追加しない / 追加する | `False` / `True` |

JSON文字列の`"true"`／`"false"`や整数の`0`／`1`は使用しない。モデルから画面へ反映するときは`findData(bool_value)`で選択位置を求め、該当候補が存在しない場合は先頭項目へ黙って移動せず診断する。

Unicode正規化が無効な間は形式ComboBoxを無効化し、保存用モデルには`None`を渡す。画面内では直前の選択を一時保持してもよいが、再び有効化して利用者が確認するまで保存値とはしない。

将来、別の`Literal`または`Enum`項目が追加された場合も同じ方式を使用する。候補はWidget内へ重複して手書きせず、モデル側の定数または専用の選択肢定義から構築する。

JSONを直接編集して未知の規定値が保存されていた場合は、その値をComboBoxへ臨時候補として追加したり先頭候補へ黙って置き換えたりしない。Loader／Bridge／Validatorの診断として表示し、利用者に正規候補を選び直してもらう。

### `null`と空文字列の区別

次の2つは意味が異なる。

```json
"置換文字列": null
```

```json
"置換文字列": ""
```

このため、除外文字列と置換文字列には使用有無のBoolean ComboBoxを付ける。

```text
[使用しない ▼] → None / JSON null
[使用する ▼] + 空欄 → "" / 一致部分を削除
[使用する ▼] + 文字あり → 入力文字列
```

Unicode正規化が有効な場合:

- 「置換文字列を使用」を自動的に無効化する。
- 値は`None`としてGUI用モデルへ渡す。
- 以前の入力文字列は画面内の一時値として保持してもよいが、保存対象にはしない。

除外文字列についても同じNullable制御を使用する。

### 入力時の動作

- 入力のたびにGUI用モデルを更新する。
- 300ms程度のDebounce後にNormalizer／Validatorを実行する。
- Errorでも入力を元へ戻さない。
- Validatorは診断だけを返し、Widgetを直接変更しない。
- 正規表現色分けは既存`RegexInputEdit`を再利用する。
- `regular_expression=false`のときはRegex色分けを無効化する。

## 8. 上部メタデータ領域

- 形式バージョン: `QSpinBox`または`QLineEdit`。Phase 1では`1`固定・読取専用。
- マクロ名: `QLineEdit`。ウインドウタイトルとTreeルートへ反映する。
- 説明: 2～3行の`QPlainTextEdit`。
- 現在ファイルパス: 選択可能な`QLabel`または読取専用`QLineEdit`。
- フォルダ設定: Phase 1では現在のフォルダを開く／選択するボタンだけ準備し、永続設定は後段で接続する。

## 9. 下部診断領域

### 使用Widget

`QTableWidget`を使用する。

列:

1. レベル
2. 手順
3. 項目
4. 内容

### 動作

- `MacroValidationResult.diagnostics`を表示する。
- Error、Warning、Informationで色とアイコンを変更する。
- 行をダブルクリックすると、該当手順を選択して対象入力欄へフォーカスする。
- `message_key`はTranslatorで日英表示へ変換する。
- `values`は翻訳文字列の埋め込み値として使用する。
- 表示順はValidatorが返した順序を維持する。
- Error件数とWarning件数をステータスバーへ表示する。

## 10. 新規ファイル設計

### Domain／GUIデータ境界

#### `macro/editor_data_model.py`

GUI編集中の可変データを保持する。

予定クラス:

```python
@dataclass(slots=True)
class MacroEditorStepData:
    step_name: str
    enabled: bool
    regular_expression: bool
    unicode_normalize: bool
    unicode_normalize_form: NormalizationForm | None
    append_dot_to_circled_number: bool
    search_text: str
    exclusion_enabled: bool
    exclusion_text: str
    replacement_enabled: bool
    replacement_text: str


@dataclass(slots=True)
class MacroEditorDocumentData:
    format_version: int
    macro_name: str
    description: str
    steps: list[MacroEditorStepData]
```

GUIでの並べ替えが必要なため、`steps`は可変`list`とする。ファイル用`MacroJsonData.steps`の`tuple`とは分離する。

#### `macro/editor_bridge.py`

```text
MacroEditorDocumentData ⇄ MacroJsonData
```

責務:

- Nullable Boolean ComboBoxと`None`の変換。
- GUIの`list`とファイルモデルの`tuple`の変換。
- GUI用可変モデルとファイル用モデルの分離。

担当しない処理:

- JSON読込・保存。
- 正規表現コンパイル。
- Validator規則。
- Widget操作。

#### `macro/editor_session.py`

現在の編集セッション状態を保持する。

予定クラス:

```python
@dataclass(slots=True)
class MacroEditorSession:
    document: MacroEditorDocumentData
    load_file_path: Path | None
    save_file_path: Path | None
    macro_folder: Path
    modified: bool
    validation_result: MacroValidationResult
```

ファイルパスには既存の命名規則どおり`load_file_path`と`save_file_path`を使用する。

### GUI Widgets

#### `dialogs/macro_step_editor_widget.py`

右ペインの手順入力部品だけを担当する。

予定Signal:

```python
step_changed = Signal(MacroEditorStepData)
field_focus_requested = Signal(str)
```

JSON、Loader、Saver、Loggerを直接参照しない。

#### `dialogs/macro_diagnostic_table.py`

診断表の表示と、選択された診断位置の通知だけを担当する。

予定Signal:

```python
diagnostic_activated = Signal(int, str)
```

第1引数は`step_index`、第2引数は`field_name`。

#### `dialogs/macro_editor_window.py`

独立ウインドウのWidget配置、メニュー、ツールバー、Tree、ステータス表示を担当する。

予定Signal:

```python
new_requested = Signal()
open_requested = Signal()
save_requested = Signal()
save_as_requested = Signal()
validate_requested = Signal()
close_requested = Signal()
step_add_requested = Signal()
step_duplicate_requested = Signal(int)
step_delete_requested = Signal(int)
step_move_requested = Signal(int, int)
```

Loader／Saverを直接呼ばない。

#### `dialogs/macro_editor_controller.py`

Qt固有の編集フローを調整する。

依存関係:

```text
MacroEditorWindow
MacroEditorSession
MacroEditorBridge
MacroJsonLoader / MacroJsonSaver
MacroNormalizer / MacroValidator
Translator
AppLogger
```

Controllerだけがファイルダイアログ、確認ダイアログ、Logger、Loader／Saverを接続する。

## 11. 既存ファイルの変更予定

### `main.py`

- 「マクロ」メニューを追加する。
- 「疑似マクロエディター」Actionを追加する。
- `self.macro_editor_window`とController参照を保持する。
- 既存ウインドウがある場合は再利用する。

MainWindowはマクロJSON変換や検証を実装しない。

### `resources/app_text_ja.json`

- ウインドウ名。
- 各入力項目名。
- メニュー／ボタン。
- 診断レベル。
- 未保存確認。
- Loader／Saverエラー表示。
- Validatorの`message_key`。

### `resources/app_text_en.json`

日本語と同じキーを英語で定義する。

### `settings/settings_manager.py`

GUI実装の最終段階で次を追加する。

```python
macro_folder: str
macro_editor_geometry: str
macro_editor_splitter_state: str
```

初期実装では`MacroJsonLoader()`／`MacroJsonSaver()`の既定値`app_base_dir()/macro`を使用し、設定が未定義でも動作させる。

### `regex-pad.spec`

新しい`macro.editor_*`と`dialogs.macro_*`を明示的Hidden Importへ追加する。翻訳JSONは既存Resources収集処理を使用する。

## 12. 読み込みフロー

```text
「開く」
  ↓
未保存変更があれば確認
  ↓
QFileDialog（開始位置はsession.macro_folder）
  ↓
MacroJsonLoader.load()
  ├ 構文／重複キー／構造Error
  │   ↓
  │ Loggerへ記録 + ダイアログ表示
  │ 現在の編集内容を維持
  │
  └ MacroJsonData
      ↓
    MacroNormalizer.normalize()
      ↓
    MacroValidator.validate()
      ↓
    MacroEditorBridge.from_json_model()
      ↓
    Session更新
      ↓
    Tree／フォーム／診断表更新
```

意味的なErrorを持つ`MacroJsonData`は、構造変換に成功していれば編集画面へ表示して修正できる。ただし保存・実行可否はValidator結果で制御する。

## 13. 保存フロー

```text
「保存」
  ↓
Widget値をMacroEditorDocumentDataへ反映
  ↓
MacroEditorBridge.to_json_model()
  ↓
MacroNormalizer.normalize()
  ↓
MacroValidator.validate()
  ├ Errorあり
  │   ↓
  │ 診断表へ表示 / 保存しない
  │
  └ Errorなし
      ↓
    Warning表示（保存は禁止しない）
      ↓
    MacroJsonSaver.save()
      ↓
    session.modified = False
      ↓
    タイトル／ステータス更新
```

保存失敗時はControllerが`MacroJsonSaveError`を捕捉し、Loggerへ記録してダイアログを表示する。Loggerの返り値を保存成功判定へ使用しない。

### 13.1 エディター入力後の`ValueError`フォールバック

WidgetからGUI用dataclassまたは`MacroJsonData`へ値を反映するとき、setter、GUI Bridge、Normalizerなどが入力値に対して`ValueError`を送出する場合がある。この例外のフォールバック先はControllerを境界としたGUIとし、アプリケーション終了、無条件の`None`返却、前回値への黙示的な差し替えは行わない。

```text
利用者が入力／「検証」／「保存」
  ↓
Widgetの未確定文字列を取得
  ↓
GUI用dataclass／GUI Bridgeへ反映
  ├ ValueError
  │   ↓
  │ 入力文字列をWidgetに保持
  │   ↓
  │ Error診断へ変換
  │   ↓
  │ 該当手順をTreeで選択
  │   ↓
  │ 該当項目を強調・フォーカス
  │   ↓
  │ 再入力を促す / 保存・実行しない
  │
  └ 変換成功
      ↓
    Normalizer／Validator／Saverへ進む
```

GUIへ返す診断には、少なくとも次の位置情報を含める。

- `step_index`: 対象手順。マクロ名など文書全体の項目では`None`。
- `field_name`: フォーカスを戻す入力項目名。
- `message_key`: 日本語／英語表示へ変換するキー。
- `format_values`: 許可値や実際の入力値など、メッセージの補足値。

表示動作は次のとおりとする。

1. 診断表にErrorを追加する。
2. 対象手順をTreeで選択し、右側フォームを表示する。
3. 対象Widgetへエラー状態の外観とツールチップを設定する。
4. 対象Widgetへフォーカスを移す。短い1行入力では原則として全文選択し、複数行の検索・除外・置換欄では入力を消さずに該当欄へカーソルを移す。
5. ステータス欄へ「入力内容を修正してください」と表示する。

入力値を失わないことを優先し、例外発生前の正常モデルで入力Widgetを上書きしない。正常モデルと未確定の画面入力はSession上で区別し、変換に成功するまで保存対象モデルを更新しない。

キー入力のたびにモーダルダイアログを開かない。通常は項目強調、診断表、ステータス表示で再入力を促し、利用者が明示的に「保存」を押したときだけ、保存できなかった旨を追加表示してもよい。

## 14. 新規作成フロー

新規マクロの初期値:

```text
format_version = 1
macro_name = ""
description = ""
steps = [新規手順1件]
```

新規手順:

```text
step_name = "step_1"
enabled = True
regular_expression = False
unicode_normalize = False
unicode_normalize_form = None
append_dot_to_circled_number = False
search_text = ""
exclusion_text = None
replacement_text = ""
```

検索文字列が空なので、作成直後はValidator Errorを表示する。自動的に架空の検索文字列を補完しない。

## 15. 未保存変更と閉じる処理

- 編集操作で`session.modified=True`にする。
- 保存成功時だけ`False`へ戻す。
- 新規作成、別ファイルを開く、ウインドウを閉じる前に確認する。

選択肢:

```text
[保存] [破棄] [キャンセル]
```

- 保存: Validatorを通して保存。Errorがあれば閉じない。
- 破棄: 現在操作を続行。
- キャンセル: 現在の編集を維持。

## 16. Undo／Redo

Phase 1では、各入力Widgetの標準Undo／Redoと手順追加・削除前の確認を使用する。

文書全体のCommand StackはPhase 2候補とする。最初から`QUndoStack`を導入してGUI実装を大きくしない。

## 17. Logger方針

記録対象:

- Loader／SaverのI/O例外。
- GUI Bridgeで発生した想定外例外。
- Controller内部の想定外例外。

原則として記録しないもの:

- 利用者が入力途中に発生する通常のValidator診断。
- 入力項目と原因を特定でき、GUIへ戻して再入力できる`ValueError`。
- 空の検索文字列。
- 入力途中の不完全な正規表現。

これらは診断表へ表示する。入力のたびにErrorログを生成しない。

一方、`ValueError`であっても対象手順・入力項目へ対応付けられない場合は想定外例外としてLoggerへ記録し、一般エラー表示を行う。この場合も現在の編集内容は破棄しない。

## 18. ファイル一覧

### 新規予定

```text
macro/
├─ editor_data_model.py
├─ editor_bridge.py
└─ editor_session.py

dialogs/
├─ macro_step_editor_widget.py
├─ macro_diagnostic_table.py
├─ macro_editor_window.py
└─ macro_editor_controller.py

tests/
├─ test_macro_editor_data_model.py
├─ test_macro_editor_bridge.py
├─ test_macro_step_editor_widget.py
├─ test_macro_editor_window.py
├─ test_macro_editor_controller.py
└─ test_main_window_macro_editor.py
```

### 変更予定

```text
main.py
resources/app_text_ja.json
resources/app_text_en.json
settings/settings_manager.py
regex-pad.spec
PSEUDO_MACRO_ARCHITECTURE.md
SCRIPT_STEP.md
```

## 19. 実装STEP

### STEP 1: GUI用モデルとBridge

- `MacroEditorStepData`
- `MacroEditorDocumentData`
- `MacroEditorBridge`
- Nullable文字列の往復テスト

Qtを使用せず、最初にデータ境界だけを完成させる。

### STEP 2: 手順入力Widget

- `MacroStepEditorWidget`
- Nullable Boolean ComboBox
- Unicode正規化時の制御切替
- `RegexInputEdit`再利用

### STEP 3: Treeと診断表

- 手順追加、複製、削除、上下移動
- 診断行から手順／項目へ移動

### STEP 4: 独立ウインドウ

- Toolbar
- Splitter
- メタデータ
- ステータスバー
- 未保存表示

### STEP 5: Controller

- 新規作成
- Loader
- Normalizer
- Validator
- Saver
- Logger
- 未保存確認

### STEP 6: MainWindowと翻訳

- マクロメニュー
- ウインドウの単一インスタンス管理
- 日英翻訳
- 既定Macroフォルダ

### STEP 7: 設定と最終接続

- ユーザー指定Macroフォルダ
- Geometry／Splitter状態
- PyInstaller
- GUI集中テスト

## 20. 初期実装の対象外

- マクロの実行。
- 本文への段階的反映。
- Preview。
- XMLファイル入出力。
- Raw JSONの直接編集。
- ドラッグ＆ドロップ並べ替え。
- 複数Macro Editorウインドウ。
- 文書全体の高度なUndo Stack。
- 外部オンラインサービス。

これらは、JSON編集・検証・安全保存がGUIで安定してから追加する。

## 21. 完了条件

- JSONを開き、全項目をGUIへ損失なく表示できる。
- GUI編集後、`null`と空文字列を区別して保存できる。
- 保存→再読込で`MacroJsonData`が一致する。
- 手順順序を追加・削除・複製・移動後も保持できる。
- Errorがあるモデルを保存・実行しない。
- Warningは表示し、保存を許可する。
- Loader／Saver失敗時に現在の編集内容を失わない。
- 未保存のまま閉じようとした場合に確認する。
- MainWindowを閉じずにMacro Editorを開閉できる。
- EXEでも既定`macro`フォルダとユーザー指定フォルダを使用できる。


## 22. Implementation status (2026-11-20)

The initial editor described above is implemented. Open it through the main window's Macro menu. The toolbar provides New/Open/Save/Save As, Validate and a read-only JSON view. Step editing, nullable fields, structural operations, diagnostic navigation, unsaved confirmation and portable editor settings are connected to the existing JSON boundaries.

The minimum window size is 640 x 480, with scrollable step fields. Add/Duplicate/Delete and Up/Down occupy separate rows so the outline can remain narrow. The JSON view is a read-only dialog. Macro execution and article changes are intentionally outside this editor implementation.

Validation and canonical propagation results are recorded in SCRIPT_STEP.md, Step15-section72. Packaged EXE and physical GUI acceptance have not been performed.


## 23. Completed macro editing operations (2026-11-21)

This section supersedes the Phase 2 deferral for drag ordering and document-wide macro-definition Undo/Redo. Both operations are implemented, alongside the execution preview/application described in the latest architecture section.

- Only step nodes can be dragged, within the same outline. Drops before/after steps, onto the root (first position) and into empty space (last position) preserve the flat step hierarchy.
- A shared QUndoStack records the entire definition, including metadata and every step field, structural changes and selection restoration. Toolbar/Edit-menu actions, keyboard shortcuts and text-input context menus address the same stack.
- Undoing to the saved definition clears the dirty marker. New/Open resets history only after confirmation/success; failed Open/Save and cancelled operations retain history.
- Article application still uses its own one-edit-block Undo, separately from macro-definition editing.

## 24. User-facing Search/Replace Presets (2026-11-21)

The window title is Search/Replace Presets / 検索/置換プリセット. It is reached from a four-action submenu under Search rather than a top-level Macro menu. Open and Run first loads the preset into this editor; the user checks the steps and presses Run Preview here. The Find/Replace dialog's Save Current Search/Replace Conditions as Preset button creates an unsaved, one-step format-2 definition. The user enters a name and chooses Save to write the new JSON. Format-2 step fields include case, whole-word, selected-only and visible-only options. The definition history and safe preview/application flow remain in charge of edits and article changes.
