from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from .config import settings
from .routers import players, doskaz, cards, submissions, admin
from .staff import routes as staff_routes, review as staff_review
from .staff.auth import LoginRequired

app = FastAPI(title="Meme Hunter Backend")

# Staff pages (reviewers, admins): login cookie, CSS/JS, routes under /staff
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="mh_staff",
    max_age=12 * 60 * 60,  # 12 hours
    same_site="lax",
    https_only=settings.session_https_only,
)
app.mount("/staff/static", StaticFiles(directory=Path(__file__).parent / "static"), name="staff_static")
app.include_router(staff_routes.router)
app.include_router(staff_review.router)


@app.exception_handler(LoginRequired)
async def staff_login_required(request: Request, exc: LoginRequired):
    return RedirectResponse("/staff/login", status_code=303)

app.include_router(players.router) #including the players router in the main application
app.include_router(doskaz.router) #including the doskaz router in the main application
app.include_router(cards.router) #including the cards router in the main application
app.include_router(admin.router) #including the admin router in the main application
app.include_router(submissions.router) #including the submissions router in the main application

@app.get("/health")
async def health():
    return {"status": "ok"}

