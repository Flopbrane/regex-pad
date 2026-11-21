# モジュールクリーナーの同時exe化を復旧

## 原因

添付プロジェクトの現在の `regex-pad.spec` は `main.py` のexe化だけを指定していました。
履歴上の `2c03c76` には `module_cleaner.py` 用の Analysis・EXE と同梱指定がありましたが、現在のspecからは抜けています。

## 適用

1. 起動しているregex-padとモジュールクリーナーを終了します。
2. プロジェクト直下の `regex-pad.spec` の控えを別の場所へコピーします。
3. このZIP内の `regex-pad.spec` を、`main.py` と同じフォルダーへコピーして差し替えます。
4. いつものプロジェクトフォルダーで、PowerShellから再ビルドします。

```powershell
.\build.ps1
```

生成先:

- `dist\regex-pad\regex-pad.exe`
- `dist\regex-pad\module_cleaner.exe`

共通の実行時ファイルは同じフォルダー内の `_internal` に入ります。
配布時は `dist\regex-pad` フォルダー全体を扱ってください。

前回修正した `dialogs/regex_input_edit.py` は、そのまま保持してください。
署名済みの `build.ps1` は今回変更しません。

## 変更点

- クリーナー専用の Analysis と PYZ を復旧。
- `module_cleaner.exe` は従来どおりコンソール付きで生成。
- 本体とクリーナーのEXE、バイナリー、データを1つのCOLLECTで同梱。
- 本体のアイコン・JSON・resources・assetsの既存設定は維持。

構成の参考: https://pyinstaller.org/en/stable/spec-files.html#multipackaging-with-one-folder-apps

## 確認

こちらでは元の添付specとの差分と `git diff --check`、ZIPの整合性を確認しました。
AGENTS.md指定のWindowsのPython環境を使えないため、Windows用exeのビルド・起動、pytest・Ruff・Pyrightは未実施です。

ZIP内の `tests/test_pyinstaller_spec.py` は検証用です。使用する場合はプロジェクトの同名ファイルへ差し替えます。
追加したテストはPyInstallerを実行せずspecの組み立てを確認します。Windows用exeの動作確認は別途必要です。

```powershell
& "D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests/test_pyinstaller_spec.py
```

ビルド後、削除を行わずにクリーナーの起動を確認する場合:

```powershell
.\dist\regex-pad\module_cleaner.exe --dry-run
```

この確認は診断レポートを作成しますが、削除処理は実行しません。
クリーナーは元からコマンドライン用です。ダブルクリックだけでは必須引数がないため終了します。
