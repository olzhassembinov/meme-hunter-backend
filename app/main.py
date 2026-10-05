from fastapi import FastAPI
from .routers import doskaz #importing the doskaz router from the routers package

app = FastAPI(title="Meme Hunter Backend")
app.include_router(doskaz.router) #including the doskaz router in the main application


@app.get("/health")
async def health():
    return {"status": "ok"}

