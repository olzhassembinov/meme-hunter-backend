from fastapi import FastAPI

app = FastAPI(title="Meme Hunter Backend")


@app.get("/health")
async def health():
    return {"status": "ok"}