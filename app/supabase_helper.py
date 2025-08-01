import requests
import json

class SupabaseHelper:
    def __init__(self, url, api_key, bucket, object_name="data.json"):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.bucket = bucket
        self.object_name = object_name

    def upload(self, data: dict) -> bool:
        headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "x-upsert": "true"
        }
        full_url = f"{self.url}/storage/v1/object/{self.bucket}/{self.object_name}"
        try:
            response = requests.put(full_url, headers=headers, data=json.dumps(data, ensure_ascii=False).encode("utf-8"))
            if response.ok:
                print("✅ データをSupabaseにアップロードしました")
                return True
            else:
                print(f"❌ アップロード失敗: {response.status_code} {response.text}")
                return False
        except Exception as e:
            print(f"❌ アップロード中にエラー: {e}")
            return False

    def download(self) -> dict:
        headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}"
        }
        full_url = f"{self.url}/storage/v1/object/public/{self.bucket}/{self.object_name}"
        try:
            response = requests.get(full_url, headers=headers)
            if response.ok:
                print("✅ Supabaseからデータを取得しました")
                return json.loads(response.content.decode("utf-8"))
            else:
                print(f"❌ ダウンロード失敗: {response.status_code} {response.text}")
                return {}
        except Exception as e:
            print(f"❌ ダウンロード中にエラー: {e}")
            return {}
