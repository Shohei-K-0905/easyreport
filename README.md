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

## 環境設定

本アプリケーションは、APIキーなどの機密情報を環境変数を通じて設定します。

1.  プロジェクトルートにある `.env.example` ファイルをコピーして `.env` という名前のファイルを作成します。
    ```bash
    cp .env.example .env
    ```
2.  作成した `.env` ファイルを開き、各変数に必要な値を設定してください。各変数の意味については、`.env.example` 内のコメントを参照してください。
3.  `.env` ファイルは `.gitignore` に含まれているため、Gitリポジトリにはコミットされません。

## 2. セットアップ済みの内容
フォルダ／ファイル生成
mkdir -p src tests models && touch … でツリーを作成。

仮想環境
.venv を作り source .venv/bin/activate （Win: Activate.ps1）。

依存リスト
requirements.txt に主要パッケージを列挙（Flask, SQLAlchemy, APScheduler, pyttsx3, vosk, msal …）。

Git 初期化
git init → .gitignore 設定 → 最初のコミット済み。

## 3. セットアップ手順
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

# 3) .env ファイルの設定
# 上記の「環境設定」セクションに従って、`.env` ファイルを作成・編集してください。

# 4) データベースの初期化
# 初回起動時に、`src/app.py` が `DATABASE_URL` (.env で設定) に基づいて自動的にデータベースファイルとテーブルを作成します。
# 手動での初期化は不要です。

## 起動方法

1.  仮想環境を有効にします。
    ```bash
    source .venv/bin/activate  # macOS/Linux
    # または
    .venv\Scripts\Activate.ps1 # Windows (PowerShell)
    ```
2.  Flask 開発サーバーを起動します。
    ```bash
    python3 -m flask --app src/app run --port=5001
    ```
    *   `.env` ファイルで `PORT` を変更している場合は、そのポート番号を指定してください。
3.  Web ブラウザで `http://127.0.0.1:5001/` にアクセスします。

## 4. 次の開発フェーズ（Phase 1 以降）

### ローカル Excel ファイルを開く機能の設定

スケジュール実行時に特定のローカル Excel ファイルを開く機能を利用するには、以下の設定が必要です。この設定は、異なる OS (macOS, Windows) や異なるユーザー環境でアプリケーションを利用する場合に特に重要です。

1.  **ベースパスの設定 (`.env` ファイル):**
    *   各ユーザーは、Excel ファイルを保存しておくフォルダ（ベースパス）を自分のコンピュータ上に決定します。
    *   そのフォルダの**絶対パス**を、プロジェクトルートにある `.env` ファイルに `EXCEL_BASE_PATH` という名前の環境変数として追加します。ファイルが存在しない場合は作成してください。
    *   例:
        *   macOS の場合: `EXCEL_BASE_PATH=/Users/your_username/Documents/EasyReportFiles`
        *   Windows の場合: `EXCEL_BASE_PATH=C:\Users\your_username\Documents\EasyReportFiles`
        *   **注意:** `.env` ファイルは `.gitignore` に含まれており、Git リポジトリにはコミットされません。各ユーザーが自分の環境に合わせて設定する必要があります。

2.  **UI でのファイル名入力:**
    *   アプリケーションの UI (スケジュール追加/編集フォーム) の「Excel Filename」フィールドには、上記で設定したベースパス（`EXCEL_BASE_PATH` で指定したフォルダ）からの**ファイル名のみ**を入力します。
    *   例: `monthly_report.xlsx`, `data/summary.xlsx`
    *   絶対パス（例: `/Users/.../file.xlsx` や `C:\...`) を入力する必要はありません。

この設定により、アプリケーションは実行時に `.env` ファイルからベースパスを読み込み、データベースに保存されているファイル名と結合して、各ユーザーの環境で正しいファイルパスを特定し、Excel ファイルを開くことができます。
