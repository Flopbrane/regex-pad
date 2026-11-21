# 検索・置換入力欄の枠外ドラッグ対策（2026-10-17）

## 適用方法

1. エディターを終了します。
2. 既存の `dialogs/regex_input_edit.py` を別の場所へコピーして控えを残します。
3. このZIP内の `dialogs/regex_input_edit.py` を、プロジェクト内の同じ場所へコピーして置き換えます。
4. 通常どおり `python .\main.py` で起動します。
5. 検索欄・置換欄それぞれに文字を入れ、上下左右の枠外までドラッグして表示と入力を確認します。
6. 複数行、長い正規表現、全置換後の再入力も確認してください。

実行時に必要な差し替えは `dialogs/regex_input_edit.py` の1ファイルです。
`tests` 内の2ファイルは開発時の検証用です。使用する場合はプロジェクト内の `tests` へコピーしてください。

## ログで確認できたこと

- 13:07:34.541 に、検索欄の縦スクロール位置が 0 から 1 に変わり、`first_visible_block` が 0 から -1 に変化しました。
- この時点で文字数は10文字、フォーカスは有効、読み取り専用は無効でした。
- その後も文字数は削除・入力に応じて変化しており、アプリケーションのイベント処理も継続していました。
- 13:09:00.729 にスクロール位置が0へ戻ると、表示先のブロック番号も0へ復帰しています。
- 比較用の標準入力欄は高さ120px、独自入力欄は高さ28pxだったため、両者の差だけでQt本体の不具合や色付け処理の不具合を断定することはできません。

文字が消えるときに「表示先の有効な行を失っている」ことはログで確認できました。
その発生条件として、固定値 `+12` による小さい入力欄の高さ計算が疑われます。

## 変更内容

- 高さはフォントの高さ・行間隔・文書余白・実際の枠幅から計算し、丸め誤差用の余裕も追加しました。
- スクロール後に表示先の行が無効になった場合だけ、先頭へ戻して再描画します。
- フォーカスなどによる表示更新時にも、無効な表示位置が残っていれば戻します。
- 既存の高さテストを余白と枠幅に対応させ、単一行・枠外ドラッグ・旧サイズでの復帰・通常の複数行スクロールの回帰テストを追加しました。

## 検証状況

差分の空白・書式チェック（`git diff --check`）とZIPの整合性確認のみ実施しました。
プロジェクトの AGENTS.md で指定されているWindowsのPython環境をこちらから使用できないため、pytest・Ruff・PyrightとWindows実機の動作確認は未実施です。修正済みと確定した版ではなく、ログの異常に対処する確認用の修正です。

指定環境での検証例（プロジェクトフォルダーでPowerShellから実行）:

```powershell
& "D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests/test_find_replace_dialog.py tests/test_regex_input_scroll.py tests/test_regex_input_display_flow.py tests/test_main_window_search.py
& "D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check dialogs/regex_input_edit.py tests/test_find_replace_dialog.py tests/test_regex_input_scroll.py
& "D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright
```

自動テストは既存の設定と同様に既定でoffscreenを使います。Windows 11の見た目・実際のマウス操作の確認も必要です。
前回の `diagnose_regex_input.py` もそのまま使用できます。症状が残る場合は、修正後のログで `first_visible_block` が -1 になるかを確認します。
