from fastapi import FastAPI
import uvicorn
from threading import Thread  # Thread をインポート

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Server is Online."}

# Uvicorn サーバーの起動関数
def start():
    uvicorn.run(app, host="0.0.0.0", port=8080)

# サーバーをバックグラウンドスレッドで起動する関数
def server_thread():
    t = Thread(target=start)
    t.start()

# サーバー起動
server_thread()