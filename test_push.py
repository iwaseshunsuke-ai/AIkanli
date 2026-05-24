import requests
import json
from datetime import datetime

# FastAPIサーバーのURL
BASE_URL = "http://localhost:8000"

# テスト用のDSLデータ（YAML形式を想定）
dsl_data = {
    "version": "1.0",
    "app": {
        "name": "SampleApp",
        "description": "これはサンプルアプリケーションのDSL定義です。",
        "version": "1.0.0",
    },
    "components": [
        {
            "type": "page",
            "name": "HomePage",
            "path": "/",
            "elements": [
                {"type": "header", "text": "ようこそ"},
                {"type": "button", "text": "開始", "action": "navigate:/dashboard"},
            ],
        },
        {
            "type": "page",
            "name": "Dashboard",
            "path": "/dashboard",
            "elements": [
                {"type": "chart", "title": "売上サマリー", "data_source": "api/sales"}
            ],
        },
    ],
    "api": {
        "endpoints": [
            {
                "path": "/api/sales",
                "method": "GET",
                "response": {
                    "type": "object",
                    "properties": {
                        "sales": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "date": {"type": "string", "format": "date"},
                                    "amount": {"type": "number"},
                                },
                            },
                        }
                    },
                },
            }
        ]
    },
}

# Webhookに送信するJSONペイロード
payload = {
    "app_name": "test_app",
    "user_name": "test_user",
    "dsl_data": dsl_data,
    "timestamp": datetime.now().isoformat(),
}

# Dify WebhookエンドポイントにPOSTリクエストを送信
try:
    print("Sending test webhook request to FastAPI server...")
    print(f"URL: {BASE_URL}/webhook/dify")
    print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    response = requests.post(
        f"{BASE_URL}/webhook/dify",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    # レスポンスの表示
    print(f"\nResponse Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")

    if response.status_code == 200:
        result = response.json()
        if result.get("status") == "success":
            print(
                "\n✅ テスト成功: データが正常に保存され、GitHubにプッシュされました。"
            )
            print(f"メッセージ: {result.get('message')}")
        elif result.get("status") == "partial_success":
            print(
                "\n⚠️  パーシャル成功: データはローカルに保存されましたが、GitHubへのプッシュに失敗しました。"
            )
            print(f"メッセージ: {result.get('message')}")
            print(f"ローカルファイル: {result.get('local_file')}")
        else:
            print(f"\n❌ 予期しないレスポンス: {result}")
    else:
        print(
            f"\n❌ リクエストに失敗しました。ステータスコード: {response.status_code}"
        )
        print(f"エラーメッセージ: {response.text}")

except requests.exceptions.ConnectionError:
    print("❌ 接続エラー: FastAPIサーバーが起動していない可能性があります。")
    print(
        "FastAPIサーバーを起動してください: uvicorn main:app --reload --host 0.0.0.0 --port 8000"
    )
except Exception as e:
    print(f"❌ 予期しないエラーが発生しました: {str(e)}")
