import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # プロジェクトのルートディレクトリ
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # データ保存用のディレクトリ
    DATA_DIR: str = os.path.join(BASE_DIR, "data")

    # GitリポジトリのURL
    GIT_REPO_URL: str = os.getenv(
        "GIT_REPO_URL", "https://github.com/your-username/AIkanli-data.git"
    )

    # Gitコミットに使用するユーザー情報
    GIT_USER_NAME: str = os.getenv("GIT_USER_NAME", "AIkanli Bot")
    GIT_USER_EMAIL: str = os.getenv("GIT_USER_EMAIL", "bot@ai-kanli.com")

    # サーバー設定
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))

    # アプリケーション設定
    APP_NAME: str = "AIkanli"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    class Config:
        env_file = ".env"


settings = Settings()
