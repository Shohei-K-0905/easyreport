1. リポジトリ概要

パス	役割
.gitignore	.env, .venv/, *.db などを除外済み
.env	未コミット（API キー／Webhook などを保存）
.venv/	Python 仮想環境（ローカルのみ）
requirements.txt	依存パッケージ一覧
schema.sql	SQLite 用 CREATE TABLE スクリプト
（ER 図に基づく 8 テーブル）
app.db	空の SQLite DB （schema.sql で初期化済み or 今後作成）
models.py	SQLAlchemy ORM を書き始めるファイル（空）
config.py	.env 読み込み用ヘルパを記述予定
src/	Flask / ジョブロジック / 音声 I/O モジュールを置く
tests/	pytest 用ユニットテスト
models/	Vosk 日本語モデルなど大容量ファイルを置く想定
コミット履歴

lua
コピーする
編集する
git log --oneline
1f82244  Initial project skeleton (easyreport)
2. セットアップ済みの内容
フォルダ／ファイル生成
mkdir -p src tests models && touch … でツリーを作成。

仮想環境
.venv を作り source .venv/bin/activate （Win: Activate.ps1）。

依存リスト
requirements.txt に主要パッケージを列挙（Flask, SQLAlchemy, APScheduler, pyttsx3, vosk, msal …）。

Git 初期化
git init → .gitignore 設定 → 最初のコミット済み。

3. winds urf での引き継ぎ手順
bash
コピーする
編集する
# 0) リポジトリ取得
git clone <your_remote_url> easyreport
cd easyreport

# 1) 仮想環境
python -m venv .venv
source .venv/bin/activate          # Windows は .venv\\Scripts\\Activate.ps1

# 2) 依存インストール
pip install -r requirements.txt

# 3) DB 初期化（初回のみ）
sqlite3 app.db < schema.sql        # または scripts/init_db.py を後で用意

# 4) .env を作成してキー類をセット
cp .env.example .env               # 用意する場合
# <-- TEAMS_WEBHOOK_URL=... などを編集 -->

# 5) 動作確認
python -c "import sqlite3, os, sys; print('OK: env + db ready')"
4. 次の開発フェーズ（Phase 1 以降）

フェーズ	担当ファイル	やること
Phase 1 – DB/ORM	models.py / db.py	SQLAlchemy で 8 テーブルのモデルを定義し、接続ヘルパを実装
Phase 2 – 設定管理	config.py	.env → 設定クラスへ読み込み、SERVICE_CONFIGS を初期投入
Phase 3 – 連携モジュール	src/ms_teams.py src/graph_excel.py src/google_forms.py	Teams Webhook, Graph API, Google Forms POST ラッパを作成
Phase 4 – 音声 I/O	src/voice/	tts.py (pyttsx3) / stt.py (vosk) / dialog.py
Phase 5 – ジョブ実装	src/jobs.py	4 種類の報告ジョブ関数を実装
Phase 6 – Flask + APScheduler	src/app.py	ミニ UI とバックグラウンドスケジューラ
Phase 7 – テスト & ドキュメント	tests/, README.md	pytest 追加・README 整備
メモ

ORM は SQLAlchemy 2.0 Declarative で書くとシンプル。

Graph API の認可は msal.PublicClientApplication.acquire_token_interactive() でデバイスフローを採用。

Vosk JP 小型モデル (vosk-model-small-ja-0.22) を models/ に展開後、stt.py でパス指定。

5. 補足
.gitignore で .env, .venv/, *.db, models/* は除外済み。

バックアップ は cp app.db backups/$(date +%F).db 程度で OK。

将来 PostgreSQL へ切替え → SQLAlchemy URL を postgresql+psycopg:// に変更し Alembic でマイグレート。

