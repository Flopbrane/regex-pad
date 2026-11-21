# Codexへの指示：regex-pad WordPress囲みタグの安全化

## 目的

regex-pad の「選択範囲を囲む」機能で WordPress 用HTMLを挿入するとき、
WordPress/Gutenberg のブロック検証エラーを起こしにくい構造にする。

今回の方針では、複雑な装飾を `wp:group` として自動生成しない。
装飾付き `<div>` は原則として `wp:html`（Custom HTMLブロック）として挿入する。

## 重要方針

1. `wp:paragraph`、`wp:heading`、`wp:list` など、構造が単純で安定しているWordPressネイティブブロックは従来通り扱ってよい。
2. `border`、`padding`、`background-color`、`max-width`、`border-radius` などを持つ複雑な囲み要素は、原則 `wp:group` に変換しない。
3. 装飾付き `<div>...</div>` は、次の形式を標準テンプレートとする。

```html
<!-- wp:html -->
<div style="border:1px solid #999;padding:16px 20px;border-radius:8px;background-color:#f9f9f9;max-width:720px">
{selected_text}
</div>
<!-- /wp:html -->
```

4. 開始タグと終了タグを別々の `wp:html` ブロックとして分離しない。
   必ず1つの `wp:html` ブロック内部で開始・終了させる。
5. 既存の `wp:group` テンプレートは削除せず、「experimental」または「非推奨」として隔離してよい。
6. 既存機能を壊さない。辞書構造や右クリック挿入UIに大きな変更を加える必要はない。

## 追加したいテンプレート

### WordPress カスタムHTML枠

```html
<!-- wp:html -->
<div style="border:1px solid #999;padding:16px 20px;border-radius:8px;background-color:#f9f9f9;max-width:720px">
{selected_text}
</div>
<!-- /wp:html -->
```

### シンプル枠

```html
<!-- wp:html -->
<div style="border:1px solid #999;padding:16px">
{selected_text}
</div>
<!-- /wp:html -->
```

### 背景付き枠

```html
<!-- wp:html -->
<div style="border:1px solid #999;padding:16px;background-color:#f9f9f9">
{selected_text}
</div>
<!-- /wp:html -->
```

## テスト項目

- 選択範囲を囲んだ際、開始タグと終了タグの対応が崩れないこと。
- 日本語・英数字・改行を含む選択範囲でも壊れないこと。
- Undo/Redo が従来通り動くこと。
- 選択なしの場合の既存動作を壊さないこと。
- `wp:html` の開始・終了コメントを重複挿入しないこと。
- 既存テストがある場合は全件通すこと。
- 新規テストを追加すること。

## 今回やらないこと

- Gutenbergの `wp:group` JSON属性を自動生成・正規化する機能
- WordPressバージョンごとのGroupブロック差異への対応
- HTML/CSSの完全なバリデータ実装

まずは安全性を優先し、装飾付き囲みはCustom HTMLブロックとして扱う。
