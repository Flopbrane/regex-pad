"""アプリの使い方を参照できる画面を提供する。"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QListWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from localization.translator import Translator

HELP_TOPICS = {
    "en": [
        (
            "File",
            """# File

- New: create a new document.
- Open: open a text file.
- Open with Encoding: open a file with a selected character encoding.
- Reload: reload the current file.
- Save / Save As: save the current text.
- Unsaved text is backed up locally and can be restored on the next launch.
- New creates a new tab without discarding existing tabs.
- Right-click a tab to close it, duplicate it, or move it to a new window.
""",
        ),
        (
            "Edit",
            """# Edit

- Undo: Ctrl+Z.
- Redo: Ctrl+Y or Ctrl+Shift+Z.
- Select All: Ctrl+A.
""",
        ),
        (
            "Search / Replace",
            """# Search / Replace

- Find / Replace: Ctrl+F.
- Use Case-sensitive, Regular expression, Whole word, Search/replace only selected text, or Search only visible text as needed.
- Preview shows replacement results before applying them.
- Regex Help opens examples and can insert a pattern into the Find field.
- Use the arrow buttons next to the Find text field to move to the previous or next match.
- Replace Marked replaces the currently highlighted search markers.
""",
        ),
        (
            "Tag Insertion",
            """# Tag Insertion

- Insert Tag: Ctrl+Shift+T.
- Type in the filter field to narrow candidates.
- Use Tab or arrow keys to move through candidates.
- Press Enter to insert the selected snippet.
- Selected text is wrapped when the snippet supports it.
- The first snippet group is prioritized by file extension: .md, .html, or .wp.html.

## WordPress HTML Modes

- Normal shows the broadest WordPress HTML snippet set for ordinary editing.
- Business / Office hides snippets that are likely to depend on custom HTML, complex image rows, or float-based layouts.
- Hi-security shows only the stricter snippet set intended for safer standard WordPress blocks.
- Stricter modes hide risky snippets instead of merely moving them lower in the menu. This keeps accidental insertion less likely.
""",
        ),
        (
            "HTML Attribute Guide",
            """# HTML Attribute Guide

Use this topic as a small reference for tag hover hints and tag snippets.

## Common Attributes

| Attribute | Where it is used | Example | Notes |
| --- | --- | --- | --- |
| `href` | Links such as `<a>` | `href="https://www.example.com"` | Destination URL. Use `https://` for ordinary web links. |
| `src` | Images, video, audio | `src="images/photo.jpg"` | File path or URL to the media. The file must exist or the browser cannot show it. |
| `alt` | Images | `alt="Product photo"` | Alternative text for users who cannot see the image. Also useful when the image fails to load. |
| `class` | Most HTML tags | `class="note-box"` | A class does not change appearance by itself. It needs matching CSS such as `.note-box { ... }`. |
| `id` | Most HTML tags | `id="section-1"` | Should be unique on the page. Useful for links like `#section-1` and CSS selectors. |
| `style` | Most HTML tags | `style="color: red;"` | Inline CSS. Works without a separate CSS file, but can become hard to maintain. |
| `target` | Links | `target="_blank"` | Opens the link in a new tab/window. |
| `rel` | Links | `rel="noopener noreferrer"` | Recommended with `target="_blank"` for safety. |
| `title` | Most HTML tags | `title="Supplemental note"` | Browser tooltip text. Do not rely on it for important content. |
| `data-*` | Most HTML tags | `data-role="warning"` | Custom data for scripts or CSS selectors. |

## Writing Examples

```html
<a href="https://www.example.com">Example site</a>
<a href="https://www.example.com" target="_blank" rel="noopener noreferrer">Open in a new tab</a>
<img src="images/photo.jpg" alt="Product photo">
<p class="lead-text">Opening paragraph</p>
<section id="overview">Overview</section>
```

## CSS Needed

`class` and many layout-oriented values do not work visually unless CSS exists.

```html
<p class="lead-text">Opening paragraph</p>
```

This needs CSS such as:

```css
.lead-text {
  font-size: 1.2em;
  font-weight: 600;
}
```

Without that CSS, `class="lead-text"` is only a label.

## Common `style` Properties

| CSS property | Example | Effect |
| --- | --- | --- |
| `color` | `color: #333;` | Text color. |
| `background-color` | `background-color: #fff3cd;` | Background color. |
| `font-size` | `font-size: 16px;` | Text size. |
| `font-weight` | `font-weight: bold;` | Text weight. |
| `text-align` | `text-align: center;` | Text alignment. |
| `line-height` | `line-height: 1.6;` | Line spacing. |
| `margin` | `margin: 1em 0;` | Outer spacing. |
| `padding` | `padding: 12px;` | Inner spacing. |
| `border` | `border: 1px solid #999;` | Border line. |
| `border-radius` | `border-radius: 4px;` | Rounded corners. |
| `display` | `display: inline-block;` | Display behavior. |
| `max-width` | `max-width: 100%;` | Maximum width. |

Inline style example:

```html
<p style="color: #333; background-color: #fff3cd; padding: 12px;">
  Important note
</p>
```

## Practical Notes

- Prefer `class` when the same design is used repeatedly.
- Prefer `style` only for one-off small adjustments.
- Always write meaningful `alt` text for images.
- Use `target="_blank"` together with `rel="noopener noreferrer"`.
- CSS class names are case-sensitive in practice. Keep them simple, such as `note-box` or `lead-text`.
""",
        ),
        (
            "HTML Dictionary",
            """# HTML Dictionary

This topic is a beginner-friendly reminder for writing ordinary HTML pages, not only WordPress snippets.

## What HTML Does

- HTML describes the meaning and structure of a page.
- CSS changes appearance, such as colors, spacing, columns, and fonts.
- JavaScript adds behavior, such as buttons, form checks, menus, and dynamic updates.
- A browser reads HTML from top to bottom and builds the page from nested elements.

## Basic Page Structure

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Page title</title>
  <meta name="description" content="Short page description">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <h1>Site or page title</h1>
  </header>

  <main>
    <section>
      <h2>Section title</h2>
      <p>Body text.</p>
    </section>
  </main>

  <footer>
    <p>&copy; 2026 Example</p>
  </footer>

  <script src="main.js"></script>
</body>
</html>
```

## Important Areas

| Area | Purpose | Typical contents |
| --- | --- | --- |
| `<!doctype html>` | Declares modern HTML. | Put it at the very beginning. |
| `<html>` | Root of the page. | Use `lang` such as `lang="en"` or `lang="ja"`. |
| `<head>` | Page metadata. | `meta`, `title`, CSS links, scripts that must load early. |
| `<body>` | Visible page content. | Text, headings, images, tables, forms, scripts at the end. |

## Common Tags

| Tag | Purpose | Basic use |
| --- | --- | --- |
| `<h1>` - `<h6>` | Headings. | Use one main `<h1>`, then structure sections with `<h2>` and lower. |
| `<p>` | Paragraph. | Ordinary text blocks. |
| `<br>` | Forced line break. | Use sparingly; prefer paragraphs for normal text. |
| `<hr>` | Thematic break. | Separates topics. |
| `<strong>` | Important text. | Usually bold by default. |
| `<em>` | Emphasized text. | Usually italic by default. |
| `<small>` | Side note or fine print. | Legal note, footnote-like text. |
| `<mark>` | Highlighted text. | Draws attention to a phrase. |
| `<a>` | Link. | Needs `href`. |
| `<img>` | Image. | Needs `src`; should have `alt`. |
| `<figure>` | Figure container. | Image, chart, code sample, or media with caption. |
| `<figcaption>` | Figure caption. | Caption inside `<figure>`. |
| `<ul>` | Bullet list. | Contains `<li>`. |
| `<ol>` | Numbered list. | Contains `<li>`. |
| `<li>` | List item. | Only inside list tags. |
| `<blockquote>` | Quoted block. | Longer quotation. |
| `<cite>` | Citation source. | Title or source name, not ordinary quoted text. |
| `<code>` | Inline code. | Short code phrase. |
| `<pre>` | Preformatted block. | Keeps spaces and line breaks. |
| `<table>` | Table. | Use for tabular data, not page layout. |
| `<thead>` | Table header group. | Header rows. |
| `<tbody>` | Table body group. | Main data rows. |
| `<tfoot>` | Table footer group. | Summary/footer rows. |
| `<tr>` | Table row. | Contains cells. |
| `<th>` | Header cell. | Column or row heading. |
| `<td>` | Data cell. | Ordinary table value. |
| `<div>` | Generic block. | Use when no semantic tag fits. |
| `<span>` | Generic inline range. | Use for styling a small inline part. |

## Layout And Semantic Tags

| Tag | Purpose | Basic use |
| --- | --- | --- |
| `<header>` | Intro area for a page or section. | Logo, title, navigation. |
| `<nav>` | Navigation links. | Main menu, table of contents. |
| `<main>` | Main content. | Use once per page. |
| `<section>` | Thematic section. | Usually has a heading. |
| `<article>` | Independent article-like content. | Blog post, news item, card that can stand alone. |
| `<aside>` | Related side content. | Sidebar, note, related links. |
| `<footer>` | Footer for a page or section. | Copyright, links, metadata. |
| `<address>` | Contact information. | Contact for the page/article owner. |
| `<details>` | Collapsible disclosure. | Contains `<summary>` and hidden/visible details. |
| `<summary>` | Disclosure title. | First visible line inside `<details>`. |
| `<dialog>` | Dialog box. | Needs JavaScript to open/close in many cases. |

## Media Tags

| Tag | Purpose | Basic use |
| --- | --- | --- |
| `<picture>` | Responsive images. | Contains `<source>` and fallback `<img>`. |
| `<source>` | Media source option. | Used inside `<picture>`, `<video>`, or `<audio>`. |
| `<video>` | Video player. | Use `controls` for normal playback controls. |
| `<audio>` | Audio player. | Use `controls`. |
| `<track>` | Captions/subtitles. | Used inside `<video>` or `<audio>`. |
| `<iframe>` | Embed another page. | Maps, videos, external widgets; often restricted by services. |
| `<canvas>` | Drawing area. | Requires JavaScript. |
| `<svg>` | Vector graphics. | Inline icon/diagram; may be restricted in some editors. |

## Form Tags

| Tag | Purpose | Basic use |
| --- | --- | --- |
| `<form>` | Form container. | Contains inputs and submit controls. |
| `<label>` | Label for form control. | Connect with `for="input-id"`. |
| `<input>` | One-line input/control. | Types: `text`, `email`, `checkbox`, `radio`, `file`, `submit`. |
| `<textarea>` | Multi-line text input. | Message fields. |
| `<select>` | Drop-down list. | Contains `<option>`. |
| `<option>` | Choice item. | Inside `<select>` or `<datalist>`. |
| `<button>` | Button. | Use `type="button"` or `type="submit"`. |
| `<fieldset>` | Group form controls. | Related fields. |
| `<legend>` | Fieldset title. | First item inside `<fieldset>`. |
| `<datalist>` | Suggestions for input. | Connected by `list="id"`. |
| `<output>` | Calculation result. | Usually updated by JavaScript. |

## Head And Metadata Tags

| Tag | Purpose | Basic use |
| --- | --- | --- |
| `<title>` | Browser tab / search result title. | Required in ordinary pages. |
| `<meta>` | Metadata. | Charset, viewport, description, robots, social metadata. |
| `<link>` | External resource relation. | CSS, favicon, preload, canonical URL. |
| `<style>` | Embedded CSS. | Useful for small standalone pages. |
| `<script>` | JavaScript. | Inline script or external `src`. |
| `<base>` | Base URL for relative links. | Use carefully; it affects relative paths. |
| `<noscript>` | Fallback when JavaScript is disabled. | Message or alternate content. |

## Data Inside Tags

- Text: write it directly inside tags such as `<p>Text</p>`.
- HTML children: put other tags inside container tags such as `<section>...</section>`.
- Attributes: write settings in the opening tag, such as `<img src="photo.jpg" alt="Photo">`.
- Metadata: use `<meta>` in `<head>`.
- CSS: use `<link rel="stylesheet" href="style.css">`, `<style>...</style>`, or `style="..."`.
- JavaScript: use `<script src="main.js"></script>` or `<script>...</script>`.
- JSON data for scripts: use a non-JavaScript script type.

```html
<script type="application/json" id="page-data">
{
  "title": "Sample",
  "items": ["one", "two"]
}
</script>
```

## Meta Examples

```html
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Short page description">
<meta name="robots" content="index, follow">
<meta property="og:title" content="Social sharing title">
<meta property="og:image" content="https://www.example.com/cover.jpg">
```

## JavaScript Examples

External file:

```html
<script src="main.js"></script>
```

Inline script:

```html
<button type="button" id="hello-button">Say hello</button>

<script>
document.getElementById("hello-button").addEventListener("click", () => {
  alert("Hello");
});
</script>
```

Safer placement:

- Put scripts near the end of `<body>` when they operate on visible page elements.
- Use `defer` when loading an external script from `<head>`.

```html
<script src="main.js" defer></script>
```

## Tags Likely To Be Removed Or Restricted Outside Normal Mode

In this app, stricter WordPress modes hide snippets that are more likely to be blocked, rewritten, or unsafe in business/high-security editing. Actual WordPress behavior also depends on user role, theme, plugins, and site security settings.

| Tag or feature | Why it is risky |
| --- | --- |
| `<script>` | Allows arbitrary JavaScript. Often removed for users without high permissions. |
| Inline event attributes such as `onclick` | JavaScript inside HTML attributes is commonly blocked. |
| `<style>` | Embedded CSS can be stripped or rewritten by editors/security filters. |
| `style` attribute | Inline CSS may be partly removed depending on settings. |
| `<iframe>` | External embeds are often restricted to trusted providers. |
| `<object>`, `<embed>` | Plugin/embed containers are high-risk and often blocked. |
| `<form>`, `<input>`, `<textarea>`, `<select>`, `<button>` | Forms can conflict with CMS behavior and security policies. |
| `<svg>` with scripts or event attributes | Plain SVG may work in some contexts, but scripted SVG is risky. |
| `<canvas>` | Needs JavaScript, so it often fails where scripts are blocked. |
| `<link>` inside body | Resource loading belongs in `<head>` and may be stripped in content editors. |
| `<meta>` inside body | Metadata belongs in `<head>` and may be ignored or removed in content editors. |

## Safe Writing Habits

- Start with semantic tags: `main`, `section`, `article`, `h2`, `p`, `ul`, `table`.
- Use CSS classes for repeated designs.
- Use inline `style` only for small, one-off HTML files or temporary tests.
- Keep one clear `<h1>` for a normal full HTML page.
- Use meaningful `alt` text for images.
- Test full HTML pages in a browser, and test WordPress HTML in Gutenberg after saving.
""",
        ),
        (
            "WordPress Parameter Notes",
            """# WordPress Parameter Notes

WordPress block comments can contain JSON parameters.

```html
<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Heading</h3>
<!-- /wp:heading -->
```

These values are WordPress block attributes. They are not ordinary HTML attributes.

## Basic Rule

- Some values are read from the block comment, such as `level` on `wp:heading`.
- Some values are read from the inner HTML, such as image `src` and `alt`.
- If the block comment and HTML describe the same meaning, keep them aligned.
- When they disagree, WordPress may rewrite the block, drop a value, or show a block validation warning.

## Safer Examples

Heading level and HTML tag match:

```html
<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Heading</h3>
<!-- /wp:heading -->
```

Spacer height and CSS height match:

```html
<!-- wp:spacer {"height":"32px"} -->
<div style="height:32px" aria-hidden="true" class="wp-block-spacer"></div>
<!-- /wp:spacer -->
```

Image size and class match:

```html
<!-- wp:image {"sizeSlug":"full","linkDestination":"none"} -->
<figure class="wp-block-image size-full"><img src="sample.jpg" alt="Description"/></figure>
<!-- /wp:image -->
```

## Risky Examples

Heading parameter says level 3, but HTML is h2:

```html
<!-- wp:heading {"level":3} -->
<h2 class="wp-block-heading">Heading</h2>
<!-- /wp:heading -->
```

Spacer parameter says 64px, but HTML says 32px:

```html
<!-- wp:spacer {"height":"64px"} -->
<div style="height:32px" aria-hidden="true" class="wp-block-spacer"></div>
<!-- /wp:spacer -->
```

Image parameter says large, but class says full:

```html
<!-- wp:image {"sizeSlug":"large","linkDestination":"none"} -->
<figure class="wp-block-image size-full"><img src="sample.jpg" alt="Description"/></figure>
<!-- /wp:image -->
```

## Practical Notes

- Use only attributes that the target core block actually supports.
- Do not invent parameter names in `{}`.
- Use double quotes in JSON: `{"height":"32px"}`.
- Avoid trailing commas in JSON.
- Copying HTML from Gutenberg after saving is the safest source for dictionary snippets.
- Custom HTML blocks are different: inside `wp:html`, use ordinary HTML and avoid nested WordPress block comments.
""",
        ),
        (
            "View",
            """# View

- Line Numbers: show or hide line numbers.
- Word Wrap: wrap long lines at the editor edge.
- The status bar shows the current line, column, and character count.
""",
        ),
        (
            "Language",
            """# Language

- Switch the application display language from the Language menu.
- Open help dialogs follow the current application language.
""",
        ),
    ],
    "ja": [
        (
            "ファイル",
            """# ファイル

- 新規: 新しい文書を作成します。
- 開く: テキストファイルを開きます。
- 文字コードを指定して開く: 文字コードを選んでファイルを開きます。
- 読み直し: 現在のファイルを読み直します。
- 保存 / 名前を付けて保存: 現在の本文を保存します。
- 未保存の本文はローカルにバックアップされ、次回起動時に復元できます。
- 新規は、既存のタブを破棄せずに新しいタブを作成します。
- タブを右クリックすると、閉じる、複製、新規ウィンドウへの移動ができます。
""",
        ),
        (
            "編集",
            """# 編集

- 元に戻す: Ctrl+Z。
- やり直し: Ctrl+Y または Ctrl+Shift+Z。
- すべて選択: Ctrl+A。
""",
        ),
        (
            "検索 / 置換",
            """# 検索 / 置換

- 検索 / 置換: Ctrl+F。
- 必要に応じて、大文字小文字、正規表現、単語全体、選択範囲内だけ、表示中の範囲だけを指定できます。
- プレビューで、置換結果を実行前に確認できます。
- 正規表現ヘルプから例を確認し、検索欄へパターンを挿入できます。
- 検索欄横の矢印ボタンで、前または次の一致箇所へ移動できます。
- マーカー部分を全て置換で、現在ハイライトされている検索マーカー部分だけを置換できます。
""",
        ),
        (
            "タグ挿入",
            """# タグ挿入

- タグ挿入: Ctrl+Shift+T。
- 絞り込み欄に入力すると候補を絞り込めます。
- Tab または上下キーで候補を移動できます。
- Enter で選択中のスニペットを挿入します。
- スニペットが対応している場合、選択中の文字列を囲みます。
- .md、.html、.wp.html では拡張子に応じた候補グループが先頭になります。

## WordPress HTML モード

- Normal は通常編集向けに、もっとも広い WordPress HTML スニペット候補を表示します。
- 企業・事業所は、独自HTML、複雑な画像横並び、float系レイアウトに依存しやすい候補を隠します。
- Hi-security は、安全寄りの標準 WordPress ブロックとして扱いやすい候補だけを表示します。
- 厳しいモードでは、危険になりやすい候補を下位表示するだけでなく、候補から隠します。誤挿入を減らすためです。
""",
        ),
        (
            "HTML属性図鑑",
            """# HTML属性図鑑

タグのホバーヒントやタグ挿入スニペットで出てくる属性の小さな図鑑です。

## よく使う属性

| 属性 | 主な使用場所 | 記述例 | 補足 |
| --- | --- | --- | --- |
| `href` | `<a>` などのリンク | `href="https://www.example.com"` | リンク先URLです。通常のWebリンクでは `https://` から書きます。 |
| `src` | 画像、動画、音声 | `src="images/photo.jpg"` | 表示・再生するファイルパスまたはURLです。ファイルが無いと表示できません。 |
| `alt` | 画像 | `alt="商品写真"` | 画像が見えない場合の代替テキストです。画像読み込み失敗時にも役立ちます。 |
| `class` | 多くのHTMLタグ | `class="note-box"` | class だけでは見た目は変わりません。別途 `.note-box { ... }` のようなCSSが必要です。 |
| `id` | 多くのHTMLタグ | `id="section-1"` | ページ内で一意にします。`#section-1` のリンクやCSS指定に使えます。 |
| `style` | 多くのHTMLタグ | `style="color: red;"` | タグへ直接書くCSSです。別CSSなしで効きますが、多用すると管理しづらくなります。 |
| `target` | リンク | `target="_blank"` | リンクを新しいタブまたはウィンドウで開きます。 |
| `rel` | リンク | `rel="noopener noreferrer"` | `target="_blank"` と一緒に使う安全対策です。 |
| `title` | 多くのHTMLタグ | `title="補足説明"` | ブラウザ上の簡単な補足表示です。重要な説明は本文に書く方が安全です。 |
| `data-*` | 多くのHTMLタグ | `data-role="warning"` | スクリプトやCSS用の独自データです。 |

## 記述方法

```html
<a href="https://www.example.com">サンプルサイト</a>
<a href="https://www.example.com" target="_blank" rel="noopener noreferrer">新しいタブで開く</a>
<img src="images/photo.jpg" alt="商品写真">
<p class="lead-text">導入文</p>
<section id="overview">概要</section>
```

## CSSファイルが必要なもの

`class` やレイアウト目的の指定は、対応するCSSがないと見た目には反映されません。

```html
<p class="lead-text">導入文</p>
```

この場合は、別途CSS側に次のような指定が必要です。

```css
.lead-text {
  font-size: 1.2em;
  font-weight: 600;
}
```

CSSが無い場合、`class="lead-text"` は名前を付けているだけで、文字サイズや太字にはなりません。

## `style` でよく使うCSSプロパティ

| CSSプロパティ | 記述例 | 効果 |
| --- | --- | --- |
| `color` | `color: #333;` | 文字色を変えます。 |
| `background-color` | `background-color: #fff3cd;` | 背景色を変えます。 |
| `font-size` | `font-size: 16px;` | 文字サイズを変えます。 |
| `font-weight` | `font-weight: bold;` | 文字の太さを変えます。 |
| `text-align` | `text-align: center;` | 文字揃えを変えます。 |
| `line-height` | `line-height: 1.6;` | 行間を変えます。 |
| `margin` | `margin: 1em 0;` | 外側の余白を付けます。 |
| `padding` | `padding: 12px;` | 内側の余白を付けます。 |
| `border` | `border: 1px solid #999;` | 枠線を付けます。 |
| `border-radius` | `border-radius: 4px;` | 角を少し丸めます。 |
| `display` | `display: inline-block;` | 表示形式を変えます。 |
| `max-width` | `max-width: 100%;` | 最大幅を指定します。 |

style の記述例:

```html
<p style="color: #333; background-color: #fff3cd; padding: 12px;">
  重要なお知らせ
</p>
```

## 実用メモ

- 同じ見た目を何度も使うなら `class` が向いています。
- その場限りの小さな調整なら `style` が使いやすいです。
- 画像には、内容が分かる `alt` を入れておくと安全です。
- `target="_blank"` を使う場合は、`rel="noopener noreferrer"` も一緒に入れるのがおすすめです。
- class 名は、`note-box` や `lead-text` のように短く分かりやすくすると管理しやすくなります。
""",
        ),
        (
            "HTML辞典",
            """# HTML辞典

初心者の確認用、または「ど忘れした時」に見るためのHTML辞典です。WordPress用だけでなく、普通のHTMLページを書く時にも使えます。

## HTMLの役割

- HTMLは、ページの意味と構造を書きます。
- CSSは、色、余白、段組み、フォントなどの見た目を変えます。
- JavaScriptは、ボタン操作、入力チェック、メニュー開閉、動的表示などの動きを足します。
- ブラウザはHTMLを上から読み、入れ子になった要素としてページを組み立てます。

## 基本のページ構造

```html
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ページタイトル</title>
  <meta name="description" content="ページの短い説明">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <h1>サイト名またはページ名</h1>
  </header>

  <main>
    <section>
      <h2>セクション見出し</h2>
      <p>本文です。</p>
    </section>
  </main>

  <footer>
    <p>&copy; 2026 Example</p>
  </footer>

  <script src="main.js"></script>
</body>
</html>
```

## 重要な場所

| 場所 | 目的 | よく入るもの |
| --- | --- | --- |
| `<!doctype html>` | 現代のHTMLとして扱う宣言です。 | ファイルの一番先頭に書きます。 |
| `<html>` | ページ全体の根っこです。 | `lang="ja"` や `lang="en"` を指定します。 |
| `<head>` | ページ情報を書く場所です。 | `meta`、`title`、CSSリンク、早めに必要なscript。 |
| `<body>` | 画面に見える本文を書く場所です。 | 文章、見出し、画像、表、フォーム、末尾のscript。 |

## よく使うタグ

| タグ | 目的 | 使い方 |
| --- | --- | --- |
| `<h1>` - `<h6>` | 見出し。 | `<h1>` は主見出し、以降は階層に合わせて使います。 |
| `<p>` | 段落。 | 通常の本文ブロック。 |
| `<br>` | 強制改行。 | 通常の段落分けには `<p>` を使い、`<br>` は控えめにします。 |
| `<hr>` | 話題の区切り。 | 章や話題を区切ります。 |
| `<strong>` | 重要な語句。 | 多くのブラウザでは太字になります。 |
| `<em>` | 文脈上の強調。 | 多くのブラウザでは斜体になります。 |
| `<small>` | 補足や注記。 | 小さめの注記、細則など。 |
| `<mark>` | ハイライト。 | 読者に注目してほしい語句。 |
| `<a>` | リンク。 | `href` が必要です。 |
| `<img>` | 画像。 | `src` が必要で、`alt` も入れるのが安全です。 |
| `<figure>` | 図版のまとまり。 | 画像、図、コード例、メディアとキャプションをまとめます。 |
| `<figcaption>` | 図版キャプション。 | `<figure>` の中に入れます。 |
| `<ul>` | 箇条書き。 | 中に `<li>` を入れます。 |
| `<ol>` | 番号付きリスト。 | 中に `<li>` を入れます。 |
| `<li>` | リスト項目。 | リストタグの中で使います。 |
| `<blockquote>` | 引用ブロック。 | 長めの引用文。 |
| `<cite>` | 引用元。 | 作品名や出典名。引用本文そのものではありません。 |
| `<code>` | インラインコード。 | 短いコードやコマンド名。 |
| `<pre>` | 整形済みブロック。 | 空白や改行を保ちます。 |
| `<table>` | 表。 | 表形式のデータに使います。レイアウト目的では使いません。 |
| `<thead>` | 表のヘッダー部分。 | 見出し行。 |
| `<tbody>` | 表の本文部分。 | 主なデータ行。 |
| `<tfoot>` | 表のフッター部分。 | 合計や注記行。 |
| `<tr>` | 表の行。 | セルを入れます。 |
| `<th>` | 見出しセル。 | 列名や行名。 |
| `<td>` | データセル。 | 通常の値。 |
| `<div>` | 汎用ブロック。 | 意味に合うタグが無い時に使います。 |
| `<span>` | 汎用インライン範囲。 | 文中の一部だけを装飾したい時に使います。 |

## レイアウト・意味づけタグ

| タグ | 目的 | 使い方 |
| --- | --- | --- |
| `<header>` | ページやセクションの導入部分。 | ロゴ、タイトル、ナビなど。 |
| `<nav>` | ナビゲーション。 | メニュー、目次、ページ内リンク。 |
| `<main>` | ページの主内容。 | 通常は1ページに1つ。 |
| `<section>` | 主題ごとのまとまり。 | 見出しを付けることが多いです。 |
| `<article>` | 独立した記事的な内容。 | ブログ記事、ニュース、単独で読めるカード。 |
| `<aside>` | 関連情報。 | サイドバー、補足、関連リンク。 |
| `<footer>` | ページやセクションの末尾。 | 著作権、リンク、補足情報。 |
| `<address>` | 連絡先情報。 | ページや記事の管理者連絡先。 |
| `<details>` | 折りたたみ開閉。 | 中に `<summary>` と詳細本文を書きます。 |
| `<summary>` | 折りたたみの見出し。 | `<details>` の最初に置きます。 |
| `<dialog>` | ダイアログ。 | 開閉にはJavaScriptが必要なことが多いです。 |

## メディア系タグ

| タグ | 目的 | 使い方 |
| --- | --- | --- |
| `<picture>` | 画面幅などに応じた画像切替。 | `<source>` と予備の `<img>` を入れます。 |
| `<source>` | メディア候補。 | `<picture>`、`<video>`、`<audio>` の中で使います。 |
| `<video>` | 動画プレイヤー。 | 通常は `controls` を付けます。 |
| `<audio>` | 音声プレイヤー。 | 通常は `controls` を付けます。 |
| `<track>` | 字幕やキャプション。 | `<video>` や `<audio>` の中で使います。 |
| `<iframe>` | 別ページの埋め込み。 | 地図、動画、外部ウィジェットなど。制限されやすいタグです。 |
| `<canvas>` | 描画領域。 | JavaScriptが必要です。 |
| `<svg>` | ベクター画像。 | アイコンや図形。環境によって制限されることがあります。 |

## フォーム系タグ

| タグ | 目的 | 使い方 |
| --- | --- | --- |
| `<form>` | フォーム全体。 | 入力欄や送信ボタンを入れます。 |
| `<label>` | 入力欄のラベル。 | `for="input-id"` で入力欄と結びます。 |
| `<input>` | 1行入力や部品。 | `text`、`email`、`checkbox`、`radio`、`file`、`submit` など。 |
| `<textarea>` | 複数行入力。 | お問い合わせ本文など。 |
| `<select>` | 選択リスト。 | 中に `<option>` を入れます。 |
| `<option>` | 選択肢。 | `<select>` や `<datalist>` の中で使います。 |
| `<button>` | ボタン。 | `type="button"` または `type="submit"` を指定します。 |
| `<fieldset>` | 入力欄のグループ。 | 関連する項目をまとめます。 |
| `<legend>` | fieldsetの見出し。 | `<fieldset>` の最初に入れます。 |
| `<datalist>` | 入力候補。 | `list="id"` でinputと結びます。 |
| `<output>` | 計算結果。 | JavaScriptで更新することが多いです。 |

## head内で使うタグ

| タグ | 目的 | 使い方 |
| --- | --- | --- |
| `<title>` | ブラウザタブや検索結果のタイトル。 | 通常ページでは必須です。 |
| `<meta>` | メタ情報。 | 文字コード、viewport、説明文、robots、SNS用情報。 |
| `<link>` | 外部リソースとの関係。 | CSS、favicon、preload、canonical URL。 |
| `<style>` | HTML内に書くCSS。 | 小さな単体ページでは便利です。 |
| `<script>` | JavaScript。 | 外部 `src` または直接記述。 |
| `<base>` | 相対URLの基準。 | 相対パス全体に影響するので慎重に使います。 |
| `<noscript>` | JavaScript無効時の表示。 | 代替案内やメッセージ。 |

## タグに内包できるデータ

- テキスト: `<p>本文</p>` のように直接書きます。
- HTMLの子要素: `<section>...</section>` のようにタグの中へ別タグを入れます。
- 属性: `<img src="photo.jpg" alt="写真">` のように開始タグへ設定を書きます。
- META情報: `<head>` 内で `<meta>` に書きます。
- CSS: `<link rel="stylesheet" href="style.css">`、`<style>...</style>`、または `style="..."` に書きます。
- JavaScript: `<script src="main.js"></script>` または `<script>...</script>` に書きます。
- スクリプト用JSON: JavaScriptとして実行しない `type` を指定して入れます。

```html
<script type="application/json" id="page-data">
{
  "title": "サンプル",
  "items": ["one", "two"]
}
</script>
```

## METAの記述例

```html
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="ページの短い説明">
<meta name="robots" content="index, follow">
<meta property="og:title" content="SNS共有用タイトル">
<meta property="og:image" content="https://www.example.com/cover.jpg">
```

## JavaScriptの記述例

外部ファイル:

```html
<script src="main.js"></script>
```

HTML内に直接書く場合:

```html
<button type="button" id="hello-button">あいさつ</button>

<script>
document.getElementById("hello-button").addEventListener("click", () => {
  alert("こんにちは");
});
</script>
```

安全寄りの置き場所:

- 画面上の要素を操作するscriptは、`body` の末尾に置くと扱いやすいです。
- `<head>` から外部scriptを読む場合は `defer` を使うと、本文読み込み後に実行されます。

```html
<script src="main.js" defer></script>
```

## Normalモード以外で消される可能性が高いタグ・機能

このアプリの厳しめの WordPress HTML モードでは、企業・事業所や Hi-security で問題になりやすいスニペットを隠します。実際にWordPressで消えるかどうかは、ユーザー権限、テーマ、プラグイン、サイトのセキュリティ設定にも左右されます。

| タグ・機能 | 危険になりやすい理由 |
| --- | --- |
| `<script>` | 任意のJavaScriptを実行できるため、権限が低いユーザーでは削除されやすいです。 |
| `onclick` などのイベント属性 | HTML属性内のJavaScriptはブロックされやすいです。 |
| `<style>` | HTML内CSSは、エディターやセキュリティ設定で削除・変更されることがあります。 |
| `style` 属性 | インラインCSSは、設定によって一部削除されることがあります。 |
| `<iframe>` | 外部埋め込みは、許可済みサービス以外だと制限されやすいです。 |
| `<object>`、`<embed>` | 埋め込み系で危険度が高く、ブロックされやすいです。 |
| `<form>`、`<input>`、`<textarea>`、`<select>`、`<button>` | CMSの動作やセキュリティ設定と衝突しやすいです。 |
| JavaScript付きの `<svg>` | 単純なSVGは通る場合もありますが、scriptやイベント属性付きは危険です。 |
| `<canvas>` | JavaScript前提のため、script禁止環境では動きません。 |
| body内の `<link>` | 外部リソース読み込みは本来 `<head>` 向けで、本文エディターでは消されることがあります。 |
| body内の `<meta>` | メタ情報は本来 `<head>` 向けで、本文エディターでは無視・削除されやすいです。 |

## 安全寄りの書き方

- まずは意味のあるタグ、`main`、`section`、`article`、`h2`、`p`、`ul`、`table` から組み立てます。
- 同じ見た目を繰り返す時はCSS classを使います。
- `style` は、小さな単体HTMLや一時確認の時だけにすると管理しやすいです。
- 普通のHTMLページでは、主見出し `<h1>` を分かりやすく1つ置きます。
- 画像には意味のある `alt` を入れます。
- 通常HTMLページはブラウザで確認し、WordPress用HTMLはGutenbergへ貼り付けて保存後の表示も確認します。
""",
        ),
        (
            "WPパラメータ記述の注意事項",
            """# WPパラメータ記述の注意事項

WordPress のブロックコメントには、JSON形式のパラメータを書けます。

```html
<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">見出し</h3>
<!-- /wp:heading -->
```

この `{}` は WordPress ブロックの属性です。通常のHTML属性とは別物です。

## 基本ルール

- `wp:heading` の `level` のように、ブロックコメント側から読む値があります。
- 画像の `src` や `alt` のように、内側のHTMLから読む値があります。
- ブロックコメント側とHTML側が同じ意味を表す場合は、必ず一致させます。
- 食い違うと、WordPress が再保存時に書き換えたり、値を落としたり、ブロック検証エラーを出すことがあります。

## 安全寄りの例

見出しレベルとHTMLタグが一致しています。

```html
<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">見出し</h3>
<!-- /wp:heading -->
```

スペーサーの高さとCSSの高さが一致しています。

```html
<!-- wp:spacer {"height":"32px"} -->
<div style="height:32px" aria-hidden="true" class="wp-block-spacer"></div>
<!-- /wp:spacer -->
```

画像サイズ指定とclassが一致しています。

```html
<!-- wp:image {"sizeSlug":"full","linkDestination":"none"} -->
<figure class="wp-block-image size-full"><img src="sample.jpg" alt="説明"/></figure>
<!-- /wp:image -->
```

## 危険な例

パラメータは level 3 ですが、HTML は h2 です。

```html
<!-- wp:heading {"level":3} -->
<h2 class="wp-block-heading">見出し</h2>
<!-- /wp:heading -->
```

パラメータは 64px ですが、HTML側は 32px です。

```html
<!-- wp:spacer {"height":"64px"} -->
<div style="height:32px" aria-hidden="true" class="wp-block-spacer"></div>
<!-- /wp:spacer -->
```

パラメータは large ですが、class は full です。

```html
<!-- wp:image {"sizeSlug":"large","linkDestination":"none"} -->
<figure class="wp-block-image size-full"><img src="sample.jpg" alt="説明"/></figure>
<!-- /wp:image -->
```

## 実用メモ

- `{}` には、そのコアブロックが実際に対応している属性だけを書きます。
- 存在しないパラメータ名を作らないようにします。
- JSONなので、文字列はダブルクォートで書きます: `{"height":"32px"}`。
- 末尾カンマは入れないでください。
- 辞書スニペットは、Gutenbergで作成して保存した後のHTMLを基準にするのが安全です。
- `wp:html` は別扱いです。中には通常のHTMLを書き、WordPressブロックコメントを入れ子にしない方が安全です。
""",
        ),
        (
            "表示",
            """# 表示

- 行番号: 行番号の表示 / 非表示を切り替えます。
- 右端で折り返す: 長い行をエディター幅で折り返します。
- ステータスバーには、現在の行、列、文字数が表示されます。
""",
        ),
        (
            "言語",
            """# 言語

- 言語メニューから表示言語を切り替えられます。
- 開いているヘルプダイアログも、現在の表示言語に追従します。
""",
        ),
    ],
}


class UserHelpDialog(QDialog):
    """操作ガイドを項目別に閲覧できる画面。"""
    def __init__(self, translator: Translator, parent: QWidget | None = None) -> None:
        """目次と本文の表示欄を組み立てる。"""
        super().__init__(parent)
        self.translator = translator
        self.resize(820, 560)

        self.topic_list = QListWidget(self)
        self.topic_list.setMaximumWidth(180)
        self.help_browser = QTextBrowser(self)
        self.help_browser.setOpenExternalLinks(False)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close,
            self,
        )
        self.button_box.rejected.connect(self.close)

        content_layout = QHBoxLayout()
        content_layout.addWidget(self.topic_list)
        content_layout.addWidget(self.help_browser, 1)

        layout = QVBoxLayout()
        layout.addLayout(content_layout)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self.topic_list.currentRowChanged.connect(self._show_topic)
        self.apply_language()

    def apply_language(self) -> None:
        """現在の言語で目次、本文、ボタン名を更新する。"""
        self.setWindowTitle(self.translator.text("help.title"))
        self.button_box.button(QDialogButtonBox.StandardButton.Close).setText(
            self.translator.text("help.close")
        )
        current_row = max(self.topic_list.currentRow(), 0)
        self._load_topics()
        self.topic_list.setCurrentRow(min(current_row, self.topic_list.count() - 1))

    def _load_topics(self) -> None:
        """使用中の言語のヘルプ項目を読み込む。"""
        self.topic_list.clear()
        language_code = "en" if self.translator.language_code == "en" else "ja"
        for title, _body in HELP_TOPICS[language_code]:
            self.topic_list.addItem(title)
        if self.topic_list.currentRow() < 0 and self.topic_list.count() > 0:
            self.topic_list.setCurrentRow(0)

    def _show_topic(self, row: int) -> None:
        """選択されたヘルプ項目の本文を表示する。"""
        if row < 0:
            self.help_browser.clear()
            return
        language_code = "en" if self.translator.language_code == "en" else "ja"
        topics = HELP_TOPICS[language_code]
        if row >= len(topics):
            return
        _title, body = topics[row]
        self.help_browser.setMarkdown(body)
