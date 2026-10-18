# ADR-004 データベース・保存・マイグレーション

| 項目 | 内容 |
|---|---|
| 状態 | 承認（D-001） |
| 日付 | 2026-10-18 |
| 作成 | Claude Code |
| 承認 | プロジェクト責任者 2026-10-18 |

## 選択肢
| 観点 | PostgreSQL ＋ SQLAlchemy 2 ＋ Alembic | SQLite | 文書の保存：ローカルのボリューム | 文書の保存：MinIO |
|---|---|---|---|---|
| ライセンス | PostgreSQL License / MIT / MIT | Public Domain | — | **AGPL-3.0** |
| 同時実行・行ロック（ワーカーのキュー） | あり | 弱い | — | — |
| JSONB（契約・トレース） | あり | 一部 | — | — |
| 運用の手間 | Docker で 1 コンテナ | 最小 | 最小 | 1 コンテナ追加 |

## 決定
- PostgreSQL（Docker Compose）、SQLAlchemy 2（ORM と Core）、Alembic。ドライバは psycopg 3（LGPL-3.0。ライブラリとしての利用で問題ないことを Phase 1 で確認）。
- 文書はローカルのボリューム（Web から配信しない）。S3 互換は将来のアダプタ。
- DB ユーザーを 2 つに分ける：マイグレーション用（DDL あり）とアプリ用（DML だけ）。
- 不変性は DB でも守る：`capability_version`・`rule_pack_version`・`dataset_version` は UPDATE・DELETE を拒否するトリガー（保険的対策）、アプリ側でも拒否（根本）。
- 保持：合成データだけなので POC の期間中は保持し、終了時に削除手順（DB とボリューム）を実行して記録する。

- 内容ハッシュ（`content_sha256`）は RFC 8785（JSON Canonicalization Scheme）で正規化した JSON の SHA-256。ファイルの改行・キーの順序・空白に左右されない。リポジトリは `.gitattributes` で改行を LF に固定する（2026-10-18 追記、RV-G0-007）。

## 影響
- テストは実際の PostgreSQL（Docker）で行う。SQLite で代用しない（挙動の差を避ける）。
- マイグレーションは CC だけが作る（`AGENTS.md`）。
