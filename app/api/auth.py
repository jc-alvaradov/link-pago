from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserRead
from app.api.deps import CurrentUser

settings = get_settings()
router = APIRouter()

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/google/login")
async def google_login(request: Request):
    redirect_uri = f"{settings.app_url}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error en autenticación con Google")

    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo obtener información del usuario")

    google_id = user_info.get("sub")
    email = user_info.get("email")
    name = user_info.get("name")
    picture = user_info.get("picture")

    user = db.query(User).filter(User.google_id == google_id).first()

    if not user:
        user = User(
            email=email,
            name=name,
            google_id=google_id,
            picture_url=picture,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.name = name
        user.picture_url = picture
        db.commit()
        db.refresh(user)

    request.session["user_id"] = str(user.id)

    return RedirectResponse(url="/", status_code=302)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Sesión cerrada"}


@router.get("/me", response_model=UserRead)
async def get_me(current_user: CurrentUser):
    return current_user
