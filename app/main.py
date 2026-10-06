from fastapi import FastAPI
from .routers import players, doskaz, cards

app = FastAPI(title="Meme Hunter Backend")
app.include_router(players.router) #including the players router in the main application
app.include_router(doskaz.router) #including the doskaz router in the main application
app.include_router(cards.router) #including the cards router in the main application

@app.get("/health")
async def health():
    return {"status": "ok"}

