# WordPress テーブルブロックのトラブル調査と修正指針

作成日: 2026-11-13  
対象: `D:\PC\Python\regex_pad_project`（Regex-Pad）と `D:\PC\Python\wp_converter`（wp-conv）

辞書を正本とする実装順序は `repair_policy_dictionary_and_table.md` を参照する。

## 1. 今回確認できた事実

ユーザー提供の「テーブルブロックのトラブル纏め.md」は、作業中の会話と試行結果を記録した資料であり、実装指示としては扱わない。記録から確認できる結果は次のとおり。

| 試行 | 観測結果 |
| --- | --- |
| `wp:table` の `<table>` または `<figure>` に幅などの `style` を直接追加 | Gutenberg で「このブロックには無効なコンテンツが含まれています」と表示 |
| `wp:html` に変更し、幅と中央寄せを指定 | 上記のブロック検証エラーは解消。ただし罫線が表示されなかった |
| `wp:html` の `<th>` と `<td>` に罫線・余白を明示 | ユーザーの WordPress 画面で罫線付きの表として表示できた |

記録中の「テーマ CSS が検証エラーの原因」という推測は、エラーの種類と合わない。CSS は表示を変えるが、Gutenberg の標準ブロック検証は保存済み HTML とブロックの `save` 出力を照合する。表示の成否、エディターでのブロック検証、保存・再読込の成否は別々に確認する必要がある。記録には WordPress のバージョン、使用テーマ、保存後の再編集結果、スマートフォン表示の実測がないため、その部分は未確認である。

資料冒頭の `\<figure>` や `\<!-- wp:table -->` のバックスラッシュは Markdown 上のエスケープ表記に見える。WordPress に投入した実際の文字列に含まれていたかは不明であり、今回の検証エラーの原因と断定しない。

## 2. 同梱 WordPress コアから分かる仕組み

Regex-Pad の `runtime/wordpress-preview/wordpress.zip` は WordPress **7.1.3** を含む。確認したのは次のファイルである。

- `wordpress/wp-includes/blocks/table/block.json`: `head`、`body`、`foot` は `<thead>`、`<tbody>`、`<tfoot>` から抽出される。`hasFixedLayout` の既定値は `true`。`spacing` の margin/padding など一部のブロック設定はサポートされる。
- `wordpress/wp-includes/js/dist/block-library.js` の `core/table` の `save`: `figure` は `useBlockProps.save()` から生成し、`table` のクラス・スタイルはブロック属性から生成する。`hasFixedLayout` が真なら `table` に `has-fixed-layout` が付く。
- `wordpress/wp-includes/blocks/table/style.css`: `.wp-block-table` に横スクロール、`.wp-block-table table` に幅 100% と罫線結合、`.wp-block-table td, .wp-block-table th` に罫線と余白を指定する。

したがって、HTML として正しい `style` でも、`wp:table` の属性に反映されず `save` が再現しない場合は無効なブロックになり得る。**すべての inline style が禁止という意味ではない。** エディターのブロック設定が正しくシリアライズしたスタイルは別である。今回のように手書きで幅を追加する方法は、少なくともユーザー環境では失敗した。

また、`wp:html` の素の `<table>` には `.wp-block-table` の CSS は当たらない。罫線消失はこのセレクターの違いで説明できる。ただし、テーマ CSS も表示に関与するため、ユーザー環境の最終的な CSS 優先順位までは未検証である。

WordPress コアを使う Regex-Pad のプレビューは**表示確認用**であり、Gutenberg エディターが行う標準ブロックの再シリアライズ検証を代行しない。

## 3. 両プロジェクトの現状とリスク

| 対象 | 現在の処理 | 修正時の要点 |
| --- | --- | --- |
| Regex-Pad `wp_conv_core/wp_blocks/wp_table.py` | Markdown 表から `<figure class="wp-block-table"><table>...` を含む `wp:table` を生成 | コア 7.1.3 の既定値 `hasFixedLayout=true` に対し、生成 HTML に `has-fixed-layout` がない。互換性や旧版用の非推奨保存形式で受理される可能性もあるため、実エディターで要検証。幅・セル装飾を足す場合は現行の標準表に直接追記しない |
| wp-conv `blocks/table.py` | 単純な表を同様の `wp:table` に変換。作業ツリーにはスタイル付き HTML 表を `wp:html` で保持する**既存の未コミット変更**がある | 既存変更を保持する。`<table>` やセルだけでなく、外側の `<figure>` / ラッパーのスタイル、キャプション、`scope`、`colspan` などを欠落させない方針が必要 |
| 両者の検査・テスト | `wp:table` の存在や HTML 構造を主に確認 | Gutenberg の再編集可否、保存後再読込、表示・罫線・幅をそれぞれ判定する |

特にコアの既定値と `has-fixed-layout` の差は、今回ユーザーが手で `style` を追加したこととは**別の潜在リスク**である。今回のエラーの唯一の原因と確定していない。既存の出力を変更する前に、実際の WordPress エディターで元の表単体も検証する。

## 4. 安定して使うための二つの経路

### A. WordPress 標準テーブルとして編集したい場合

1. WordPress のテーブルブロックで表を作り、幅・余白などはエディターが提供するブロック設定またはサイトの追加 CSS で調整する。保存済みの `wp:table` HTML に手で属性を足さない。
2. 変換器が `wp:table` を出力する場合は、対象 WordPress 版の `save` 形式に合わせ、見出し・本文・脚注、セルタグ、ブロック属性、`has-fixed-layout` を一貫して生成する。バージョン差も考慮する。
3. WordPress に貼り付け、保存し、ページを再読込してエディターを再度開く。「無効なコンテンツ」が出ないことを必須条件にする。プレビュー成功だけでは合格にしない。

幅を 600px にしたいだけなら、まず**外部 CSS** とエディターが出力するクラス・設定を検討する。対象テーマによって本文幅や table の `width:100%` が効くため、公開ページで実測する。

### B. 600px・中央寄せ・罫線などを個別指定したい場合

今回成功した経路を、装飾表の**明示的な選択肢**として採用する。`wp:html` に切り替え、幅・スクロール・罫線を自己完結させる。これは標準テーブルのセル編集 UI を使えなくするため、無条件で全表を置き換えない。

```html
<!-- wp:html -->
<div style="width:100%; max-width:600px; margin:2em auto; overflow-x:auto;">
<table style="width:100%; border-collapse:collapse; border:1px solid #999;">
<thead><tr>
<th scope="col" style="border:1px solid #999; padding:10px; background-color:#EAF4FF;">項目</th>
<th scope="col" style="border:1px solid #999; padding:10px; background-color:#EAF4FF;">A型</th>
<th scope="col" style="border:1px solid #999; padding:10px; background-color:#EAF4FF;">B型</th>
</tr></thead>
<tbody><tr>
<th scope="row" style="border:1px solid #999; padding:10px;">雇用契約</th>
<td style="border:1px solid #999; padding:10px;">あり</td>
<td style="border:1px solid #999; padding:10px;">なし</td>
</tr></tbody>
</table>
</div>
<!-- /wp:html -->
```

これは今回の表示結果に基づく**ひな形**であり、例示の 600px と色を全記事へ固定する要件ではない。幅が変わらない場合は、まず記事本文領域と表自身のどちらが広いかを切り分ける。テーマや投稿権限による HTML/CSS のフィルタリング、モバイル時のスクロール・折り返しも実サイトで確認する。`<div>` の扱いに問題がある環境では、`<table>` に幅を指定する代替案を別途試す。

## 5. 修正を進める順序と合格条件

1. **再現用の対を保存**: 元の標準表、手書きスタイルを足して無効になった表、`wp:html` で成功した表を、投稿内容と WordPress 版・テーマ・検証画面の結果付きで記録する。資料中の Markdown エスケープは実際の投入 HTML から除く。
2. **Regex-Pad と wp-conv の標準表生成を比較**: 同じ Markdown 表を両者で変換し、WordPress コアの既定値・保存形式との差を調べる。必要な最小修正を両方に適用する。既存の wp-conv の未コミット変更は保持する。
3. **装飾表の出力ルールを明示**: 幅・罫線・セル装飾・ラッパーのスタイルを維持する必要がある表は `wp:html` にする。元の表の内容・属性を捨てて「単純な表」に再構築しない。単純な無装飾表は、実エディター検証に合格した形式の `wp:table` を使える。
4. **診断を追加**: `wp:table` 内の手書き `style` など、コアの `save` と一致しない可能性が高い形を、今回の壊れた/直った対に基づく個別ルールとして警告する。正しい `wp:html` には同じ警告を出さない。見た目の不具合はエディター検証エラーと別の診断にする。
5. **合格判定**: 自動テストでは内容・属性の保持と壊れた側だけの対象診断を確認する。WordPress エディターでは貼付→保存→再読込→再編集で無効ブロックが出ないことを確認する。公開表示ではデスクトップとスマートフォンの幅・罫線・スクロールを確認する。ユーザー環境での確認までは「完全に互換」とは記さない。

### 現時点の結論

今回の直接の失敗は、`wp:table` の保存 HTML を手で変更した際のブロック検証エラーである。`wp:html` への変更はその照合を回避したが、標準テーブル向け CSS も外れたため、罫線を明示して表示を完成させた。両ツールの修正では、**標準表として再編集できる形式**と**装飾を保つ Custom HTML 形式**を別経路として扱い、実 WordPress で保存後の再編集まで検証する。
