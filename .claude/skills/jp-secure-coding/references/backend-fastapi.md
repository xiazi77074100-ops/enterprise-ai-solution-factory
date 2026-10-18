# バックエンド（FastAPI / SQLAlchemy 2 / Pydantic v2）

ライブラリの採否は ADR で決まる。ここは「採用した前提で、どう書くか」。コード例は形を示すもので、そのまま貼る前に実際の版の API を確かめる。

## 1. 入力と出力の型

```python
from pydantic import BaseModel, ConfigDict, Field

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

class ProjectCreate(StrictModel):          # 入力専用。id・owner_id・status・created_at を持たない
    name: str = Field(min_length=1, max_length=100)
    domain: Literal["invoice", "contract", "other"]   # 業務区分はデータ。エンジンの分岐に使わない

class ProjectOut(BaseModel):                # 出力専用。返してよい列だけ
    id: UUID
    name: str
```

- すべての文字列に `max_length`、配列に `max_length`、数値に範囲。上限のない入力を作らない。
- `response_model` を必ず指定する（内部の列が漏れない）。
- 日時は API では ISO-8601 UTC（`datetime` は tz-aware）。JST への変換は画面で行う。
- ID は UUID。連番を外に出さない（件数の推測・総当たりを防ぐ。ただし認可の代わりではない）。

## 2. SQL

```python
# ○ ORM / Core（バインド変数）
stmt = select(Project).where(Project.id == project_id)

# ○ どうしても text() を使うとき
stmt = text("SELECT id FROM project WHERE name = :name").bindparams(name=name)

# ○ 並び替え：利用者の値を列に対応付ける。対応にない値は 422
SORTABLE = {"updated_at": Project.updated_at, "name": Project.name}
column = SORTABLE.get(sort)
if column is None:
    raise ApiError("invalid_sort", "並び替えの項目が正しくありません。", status=422)

# ○ 部分一致：ワイルドカードをエスケープ
pattern = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
stmt = stmt.where(Project.name.ilike(pattern, escape="\\"))
```

- ✗ `text(f"... WHERE name = '{name}'")`、`order_by(text(sort))`、`.where(literal_column(user_input))`
- アプリの DB ユーザーは DDL 権限なし（マイグレーション用ユーザーと分ける）。

## 3. 外部コマンド・動的評価

- 原則使わない。OCR など外部バイナリが必要なら：

```python
subprocess.run([TESSERACT_BIN, str(tmp_in), "stdout", "-l", "jpn"],
               shell=False, check=True, capture_output=True, timeout=60)
```

  `TESSERACT_BIN` は設定の絶対パス。引数に利用者の文字列を入れない（言語コードなども許可リストから）。
- 禁止：`os.system`、`shell=True`、`eval`、`exec`、`compile`、`pickle` / `marshal` の読み込み、`yaml.load`（`yaml.safe_load` を使う）、`importlib.import_module(利用者の値)`。
- Capability の実装参照（`implementation.reference`）は **起動時に登録した許可リストのキー** として解決する。文字列から動的 import しない（`easf-capability-contract`）。

## 4. 認証・セッション・クッキー

- パスワード：argon2id（`argon2-cffi` の `PasswordHasher` 既定値以上）。最小 12 文字、上限 128 文字。平文・可逆暗号で持たない。
- ログイン：
  - 失敗の文言は 1 種類。存在しないユーザーでもハッシュ計算を 1 回行い、応答時間を揃える（ユーザー列挙対策）。
  - 同一アカウントの連続失敗（例 5 回）で一時ロック（例 15 分）。同一 IP の試行にも上限。値は設定に出す。
  - 成功したら **新しいセッション ID を発行し、古い ID を無効にする**。
- セッション：DB の `session` 表（`id_hash`、`user_id`、`created_at`、`last_seen_at`、`expires_at`、`csrf_secret`）。Cookie には乱数の ID だけ、DB には ID のハッシュ（SHA-256）を持つ。
- Cookie：

```python
response.set_cookie("__Host-easf_session", sid, secure=True, httponly=True,
                    samesite="lax", path="/", max_age=None)   # domain は付けない
```

  ローカル開発で HTTP を使う間は `__Host-` と `secure` が使えない。**設定で切り替え、HTTP のままの設定は診断対象の環境で使わない**（起動時に HTTPS 以外なら警告をログに出す）。
- ログアウト：サーバ側のセッションを削除し、Cookie を消す。パスワード変更時は他のセッションも消す。
- 権限変更（ロール付与など）は監査ログに残す。

## 5. CSRF

- Cookie で認証する API は、状態を変えるメソッド（POST / PUT / PATCH / DELETE）で次の 2 つを確かめる：
  1. ヘッダ `X-CSRF-Token` が、セッションの `csrf_secret` から作った値と一致する（`hmac.compare_digest`）。
  2. `Origin`（無ければ `Referer`）が設定の自サイトと一致する。
- トークンは `GET /api/v1/session` の応答本文で渡す。Cookie に入れて JS から読ませる方式（double submit）にするなら `__Host-` ＋ 署名付きにする。
- GET・HEAD・OPTIONS で状態を変えない。
- CORS：同一オリジン配信を基本とし、`allow_origins=["*"]` と `allow_credentials=True` を併用しない。必要な場合だけ完全一致のオリジンを列挙する。

## 6. ヘッダ・配信・リダイレクト

すべての応答に付けるミドルウェア（1 か所で実装し、テストで全エンドポイントを確かめる）：

| ヘッダ | 値 |
|---|---|
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'` |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin`（または `no-referrer`） |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |
| `Cross-Origin-Opener-Policy` | `same-origin` |
| `Strict-Transport-Security` | HTTPS で配信するときだけ `max-age=31536000; includeSubDomains` |
| `Cache-Control` | API・認証後の画面は `no-store` |

- UI ライブラリが実行時に `<style>` を挿入する場合（CSS-in-JS）、`style-src 'unsafe-inline'` が必要になり、診断で「低」〜「情報」の指摘になりやすい。nonce を付ける設定にするか、指摘として受容するかを ADR に書く。
- `uvicorn --no-server-header`（`Server: uvicorn` を出さない）。`X-Powered-By` を出さない。
- 不要な HTTP メソッド（TRACE など）は 405。ルータに無いメソッドを通さない。
- 静的配信はビルド成果物のディレクトリだけ、ディレクトリ一覧なし。アップロード領域は配信しない（ダウンロードは認可付きの API 経由）。
- `next=` などの任意リダイレクトを作らない。SPA のルーティングで足りる。

## 7. 認可

```python
router = APIRouter(dependencies=[Depends(require_user)])   # 既定で認証必須

@router.get("/projects/{project_id}")
def get_project(project_id: UUID, user: User = Depends(require_user), db: Session = Depends(get_db)) -> ProjectOut:
    project = projects.get_for_member(db, project_id, user)   # 見えない・無いは同じ 404
    ...

@router.post("/solutions/{solution_id}/approve")
def approve(..., user: User = Depends(require_role("solution_lead"))): ...
```

- **取得関数がメンバー条件を WHERE に含める**（取ってから比べるのではなく）。一覧・詳細・更新・削除・ダウンロード・トレース・評価・再利用実績のすべてで。
- 「権限なし」と「存在しない」は同じ 404 を返す（存在の推測を防ぐ）。ロール不足は 403。
- 人の確認（review）の決定は、割り当てられた確認者か役割を持つ人だけ。自分が作った解決策を自分で承認できるかは ADR-006 で決める。
- **テスト**：OpenAPI からエンドポイント一覧を作り、ロール（未ログイン・他案件のメンバー・各ロール）× エンドポイントの期待値表で全件を確かめる。新しいエンドポイントが表に無ければテストが失敗するようにする。

## 8. エラーとログ

- 共通の例外ハンドラで `{"code", "message", "trace_id", "details"}` だけを返す。`message` は日本語、`code` は英語の固定値。500 は「処理中にエラーが発生しました。（trace_id: …）」だけ。
- `RequestValidationError` の既定応答は入力値をそのまま返すので、上書きして値を返さない（項目名と理由だけ）。
- 本番相当（`EASF_ENV != "dev"`）では `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)`。OpenAPI はビルド時にファイルへ出力して契約テストに使う。
- ログは JSON の構造化ログ。パスワード・Cookie・Authorization・CSRF トークン・API キー・文書本文・口座番号を出さない（ロガーのフィルタで項目名ごとに伏せる）。利用者入力は値として記録し、改行で偽のログ行を作れないようにする。
- 監査ログ（ログイン・ロール変更・承認・確認の決定・エクスポート）は改ざん検知できる形（追記のみの表＋ハッシュ連鎖など。方式は ADR）。

## 9. 上限（資源の枯渇・コスト）

| 対象 | 既定値（ADR で確定） |
|---|---|
| リクエスト本文 | 1 MB（アップロード API は別枠） |
| 一覧の `limit` | 既定 50、最大 200 |
| アップロード | 10 MB、30 ページ |
| ノード実行時間 | Capability の `timeout_ms`、上限 120 秒 |
| リトライ | 冪等な操作だけ、最大 2 回、指数バックオフ |
| 1 実行あたりの LLM トークン・円 | 実行予算として設定、超えたら失敗（成功にしない） |
| 同時実行数 | ワーカー数で制限 |
| ログイン試行 | アカウント・IP ごとに上限 |
