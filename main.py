from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import logging
import logging.handlers
import os
import yaml
from datetime import datetime
from git import Repo
import shutil
from config.settings import settings
import difflib
import json
from typing import Dict, Any

# ロギングの設定
log_dir = os.path.join(settings.BASE_DIR, "logs")

# ログファイルの設定（ローテーション付き）
log_file = os.path.join(log_dir, "webhook.log")
handler = logging.handlers.RotatingFileHandler(
    log_file, maxBytes=10 * 1024 * 1024, backupCount=5
)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

logger = logging.getLogger("webhook")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

app = FastAPI(title=settings.APP_NAME)

# バックアップディレクトリの設定
BACKUP_DIR = os.path.join(settings.BASE_DIR, "backups")


def generate_diff(
    old_data: Dict[Any, Any], new_data: Dict[Any, Any], label: str = ""
) -> str:
    """
    2つの辞書データの差分を生成し、読みやすい形式で返す。
    YAML/JSONの構造を維持したテキスト形式の差分を作成する。

    Args:
        old_data: 古いデータ
        new_data: 新しいデータ
        label: 差分のラベル（例: "app_name"）

    Returns:
        差分を表す文字列
    """
    # 辞書をソートされたJSON文字列に変換（キー順を統一）
    old_json = json.dumps(old_data, ensure_ascii=False, indent=2, sort_keys=True)
    new_json = json.dumps(new_data, ensure_ascii=False, indent=2, sort_keys=True)

    # 行単位に分割
    old_lines = old_json.splitlines()
    new_lines = new_json.splitlines()

    # difflibで差分を生成
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"old_{label}.json",
        tofile=f"new_{label}.json",
        lineterm="",
    )

    # 差分を文字列に結合
    diff_text = "\n".join(diff)

    if diff_text:
        return f"--- 差分 ({label}) ---\n{diff_text}\n--- 差分終了 ---"
    else:
        return f"--- 差分 ({label}) ---\nデータに変更はありません。\n--- 差分終了 ---"


# ログファイルの設定（ローテーション付き）
log_file = os.path.join(log_dir, "webhook.log")
handler = logging.handlers.RotatingFileHandler(
    log_file, maxBytes=10 * 1024 * 1024, backupCount=5
)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

logger = logging.getLogger("webhook")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

app = FastAPI(title=settings.APP_NAME)

# バックアップディレクトリの設定
BACKUP_DIR = os.path.join(settings.BASE_DIR, "backups")


@app.post("/webhook/dify")
async def dify_webhook(request: Request):
    """
    DifyからのWebhookを受け取り、DSLデータをYAMLとして保存し、
    GitHubに自動プッシュするエンドポイント
    """
    try:
        # リクエストボディの取得
        body = await request.json()
        logger.info(f"Received webhook request: {body}")

        # 必須フィールドのチェック
        if not all(k in body for k in ("app_name", "user_name", "dsl_data")):
            error_msg = "Missing required fields: app_name, user_name, dsl_data"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)

        app_name = body["app_name"]
        user_name = body["user_name"]
        dsl_data = body["dsl_data"]

        # バックアップディレクトリの作成
        app_backup_dir = os.path.join(BACKUP_DIR, app_name)
        os.makedirs(app_backup_dir, exist_ok=True)

        # アプリ名に対応する最新のYAMLファイルを取得
        yaml_files = []
        try:
            yaml_files = [f for f in os.listdir(app_backup_dir) if f.endswith(".yaml")]
            yaml_files.sort(reverse=True)  # 新しい順にソート
        except Exception as e:
            logger.error(f"Error reading backup directory: {str(e)}")
            logger.info(
                f"No previous DSL data found for {app_name}. This is the first save."
            )
            # その他のエラーが発生した場合は空のリストを返す
            yaml_files = []

        if yaml_files:
            latest_yaml_path = os.path.join(app_backup_dir, yaml_files[0])
            with open(latest_yaml_path, "r", encoding="utf-8") as f:
                old_dsl_data = yaml.safe_load(f)

            # 差分を生成してログ出力
            diff_result = generate_diff(old_dsl_data, dsl_data, app_name)
            logger.info(f"DSL data diff:\n{diff_result}")
        else:
            logger.info(
                f"No previous DSL data found for {app_name}. This is the first save."
            )

        # アプリ名のバリデーション（セキュリティ対策）
        if not app_name.isalnum() and "_" not in app_name and "-" not in app_name:
            error_msg = f"Invalid app_name format: {app_name}"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)

        # タイムスタンプの生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # バックアップディレクトリの作成
        app_backup_dir = os.path.join(BACKUP_DIR, app_name)
        os.makedirs(app_backup_dir, exist_ok=True)

        # YAMLファイルの保存
        yaml_filename = f"{timestamp}.yaml"
        yaml_filepath = os.path.join(app_backup_dir, yaml_filename)

        # DSLデータをYAMLとして保存
        with open(yaml_filepath, "w", encoding="utf-8") as f:
            yaml.dump(
                dsl_data, f, allow_unicode=True, default_flow_style=False, indent=2
            )

        logger.info(f"DSL data saved successfully: {yaml_filepath}")

        # Gitプッシュの実行
        try:
            push_to_github(app_name, yaml_filename)
            logger.info(f"Successfully pushed to GitHub: {app_name}/{yaml_filename}")
            return JSONResponse(
                content={
                    "status": "success",
                    "message": f"DSL data saved and pushed to GitHub: {app_name}/{yaml_filename}",
                },
                status_code=200,
            )
        except Exception as e:
            error_msg = f"Failed to push to GitHub: {str(e)}"
            logger.error(error_msg)
            # Gitプッシュ失敗時も200を返すが、メッセージで通知
            return JSONResponse(
                content={
                    "status": "partial_success",
                    "message": f"DSL data saved locally but failed to push to GitHub: {str(e)}",
                    "local_file": yaml_filepath,
                },
                status_code=200,
            )

    except Exception as e:
        error_msg = f"Unexpected error in webhook handler: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


def push_to_github(app_name: str, filename: str):
    """
    GitPythonを使用して、保存したYAMLファイルをGitHubにプッシュする
    """
    try:
        # リポジトリのパス
        repo_path = settings.BASE_DIR

        # 環境変数からGitHubトークンを取得
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            raise ValueError("GITHUB_TOKEN environment variable is not set")

        # GitリモートURLの生成（トークンを含む）
        repo_url = settings.GIT_REPO_URL
        if repo_url.startswith("https://"):
            repo_url = repo_url.replace("https://", f"https://{github_token}@")

        # リポジトリの初期化またはオープン
        if not os.path.exists(os.path.join(repo_path, ".git")):
            logger.info(f"Initializing new git repository at {repo_path}")
            repo = Repo.init(repo_path)
        else:
            repo = Repo(repo_path)

        # ファイルのステージング
        yaml_filepath = os.path.join(BACKUP_DIR, app_name, filename)
        repo.index.add([yaml_filepath])

        # 変更のコミット
        commit_message = f"feat: Add DSL data for {app_name} by {os.getenv('GIT_USER_NAME', 'AIkanli Bot')}"
        repo.index.commit(commit_message)

        # ユーザー情報の設定
        with repo.config_writer() as config:
            config.set_value("user", "name", settings.GIT_USER_NAME)
            config.set_value("user", "email", settings.GIT_USER_EMAIL)

        # リモートの設定（存在しない場合）
        if "origin" not in repo.remotes:
            logger.info(f"Adding remote origin: {repo_url}")
            repo.create_remote("origin", repo_url)

        # GitHubへのプッシュ
        logger.info("Pushing to GitHub...")
        origin = repo.remotes.origin
        origin.push()

        logger.info(f"Successfully pushed to GitHub: {repo_url}")

    except Exception as e:
        logger.error(f"Error in push_to_github: {str(e)}", exc_info=True)
        raise


# アプリケーションの起動イベント
@app.on_event("startup")
async def startup_event():
    """
    アプリケーション起動時の処理
    """
    logger.info("Starting up AIkanli webhook server...")
    logger.info(f"Backup directory: {BACKUP_DIR}")
    logger.info(f"Log file: {log_file}")

    # 必須ディレクトリの作成
    os.makedirs(BACKUP_DIR, exist_ok=True)
    logger.info("Required directories are ready")


# アプリケーションのシャットダウンイベント
@app.on_event("shutdown")
async def shutdown_event():
    """
    アプリケーションシャットダウン時の処理
    """
    logger.info("Shutting down AIkanli webhook server...")
