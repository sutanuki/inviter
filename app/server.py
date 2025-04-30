from fastapi import FastAPI
import uvicorn
from fastapi.responses import Response

app = FastAPI()

@app.head("/")
async def root_head():
    return Response(status_code=200)
@app.get("/")
def read_root():
    return {"message": "Server is Online."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)