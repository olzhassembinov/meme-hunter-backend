from fastapi import FastAPI
from .routers import players, doskaz, cards, submissions, admin

app = FastAPI(title="Meme Hunter Backend")
app.include_router(players.router) #including the players router in the main application
app.include_router(doskaz.router) #including the doskaz router in the main application
app.include_router(cards.router) #including the cards router in the main application
app.include_router(admin.router) #including the admin router in the main application
app.include_router(submissions.router) #including the submissions router in the main application

@app.get("/health")
async def health():
    return {"status": "ok"}

