from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.api import auth, payment_links, payments

settings = get_settings()

app = FastAPI(
    title="Link de Pago",
    description="Sistema de generación de links de pago con Webpay",
    version="1.0.0",
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="session",
    max_age=86400 * 7,  # 7 days
    same_site="lax",
    https_only=settings.is_https,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

# Routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(payment_links.router, prefix="/api/v1/links", tags=["links"])
app.include_router(payments.router, prefix="/pay", tags=["payments"])


@app.get("/")
async def root(request: Request):
    user_id = request.session.get("user_id")
    if user_id:
        return templates.TemplateResponse("dashboard.html", {"request": request})
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}
