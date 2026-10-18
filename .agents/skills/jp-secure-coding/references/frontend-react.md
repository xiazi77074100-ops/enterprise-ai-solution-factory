# フロントエンド（React / TypeScript / Vite）

## XSS

- 文字は JSX の `{value}` で出す（自動エスケープ）。
- 禁止：`dangerouslySetInnerHTML`、`element.innerHTML =`、`document.write`、`eval`、`new Function`、`setTimeout("文字列")`。ESLint で `react/no-danger` と `no-eval` `no-implied-eval` `no-new-func` をエラーにする。
- **根拠（evidence）のハイライト**：HTML を組み立てない。本文を `[{text, highlighted}]` に分けて `<mark>` を React ノードとして並べる。
- **LLM の出力・文書の本文** はプレーンテキストとして表示する。Markdown を描画する必要があれば、生 HTML を許さない設定（`react-markdown` で `rehype-raw` を使わない等）にし、リンクは下の URL 規則を通す。
- URL：`href` / `src` に入れる値は `new URL(value, location.origin)` で解析し、`protocol` が `http:` / `https:` のものだけ。`javascript:`・`data:`・`vbscript:` を通さない。外部リンクは `rel="noopener noreferrer"`。
- SVG・HTML をアップロード対象にしない（文書は PDF と画像だけ）。

## CSP に合わせる

- インラインの `<script>`・`onclick="…"` 属性・`javascript:` URL を使わない（CSP の `script-src 'self'` で動かなくなる）。
- `index.html` に外部 CDN の script / font を読ませない。フォントは同梱するか OS フォント。
- 実行時に `<style>` を挿入する UI ライブラリを使う場合は、nonce の設定方法を ADR に書く。

## 認証情報・保存

- 認証は HttpOnly Cookie（JS から読めない）。**アクセストークン・セッション ID を localStorage / sessionStorage / IndexedDB に置かない**（XSS 1 つで全部持ち出される、と診断で指摘される）。
- localStorage に置いてよいのは表示設定（列の幅・表示密度など）だけ。業務データ・文書の中身・個人情報を置かない。
- CSRF トークンはメモリ（React の状態）に持ち、状態を変える `fetch` に `X-CSRF-Token` を付ける。`fetch` は 1 つのクライアント関数にまとめ、画面ごとに書かない。
- `credentials: "same-origin"`（同一オリジン配信）。

## 画面に出してよい情報

- エラーはサーバの `message`（日本語）と `trace_id` だけを出す。例外オブジェクトやスタックを `console` / 画面に出さない。
- 本番ビルドで `console.log` を残さない（ESLint `no-console`、`warn` / `error` だけ許可）。
- 権限で隠すボタンは「見た目」の工夫であり、**守るのはサーバ**。画面の非表示を認可の代わりにしない。

## ビルド・配信

- 本番ビルドでソースマップを配信しない（`build.sourcemap: false`、または生成しても配信ディレクトリに置かない）。
- HTML コメント・JS の文字列に内部 URL・接続先・メールアドレス・秘密を残さない。環境変数は `VITE_` 接頭辞のものだけがクライアントに入る。**秘密を `VITE_` に入れない**。
- 依存関係は `package-lock.json` を固定し、`npm ci` で入れる。`npm audit --omit=dev` を CI で実行する。

## フォーム

- パスワード欄は `type="password"`・`autocomplete="current-password"`（新規は `new-password`）。貼り付けを禁止しない。
- 二重送信を防ぐ（送信中はボタンを押せない）。サーバ側でも冪等キーで防ぐ（確認の決定 API は冪等キー必須）。
- 入力チェックは画面とサーバの両方。画面のチェックは使い勝手のため、守るのはサーバ。
