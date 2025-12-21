from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc

from app.api.deps import CurrentUser, DbSession
from app.models.payment_link import PaymentLink, PaymentLinkStatus
from app.models.user import User
from app.schemas.payment_link import PaymentLinkCreate, PaymentLinkRead, PaymentLinkUpdate
from app.config import get_settings

settings = get_settings()
router = APIRouter()


# === DEV ENDPOINTS (quitar en producción) ===

class DevLinkCreate(BaseModel):
    amount: int
    description: str
    single_use: bool = True


@router.post("/dev/create", response_model=PaymentLinkRead, tags=["dev"])
async def dev_create_link(link_data: DevLinkCreate, db: DbSession):
    """Endpoint de desarrollo para crear links sin autenticación"""
    # Crear o obtener usuario de prueba
    dev_user = db.query(User).filter(User.email == "dev@test.com").first()
    if not dev_user:
        dev_user = User(
            email="dev@test.com",
            name="Dev User",
            google_id="dev_google_id_123",
        )
        db.add(dev_user)
        db.commit()
        db.refresh(dev_user)

    link = PaymentLink(
        user_id=dev_user.id,
        amount=link_data.amount,
        description=link_data.description,
        single_use=link_data.single_use,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.get("/dev/all", response_model=list[PaymentLinkRead], tags=["dev"])
async def dev_list_all_links(db: DbSession):
    """Listar todos los links (sin filtrar por usuario)"""
    return db.query(PaymentLink).order_by(desc(PaymentLink.created_at)).all()


# === FIN DEV ENDPOINTS ===


@router.post("/", response_model=PaymentLinkRead, status_code=status.HTTP_201_CREATED)
async def create_link(
    link_data: PaymentLinkCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    link = PaymentLink(
        user_id=current_user.id,
        amount=link_data.amount,
        description=link_data.description,
        single_use=link_data.single_use,
        expires_at=link_data.expires_at,
        extra_data=link_data.extra_data,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.get("/", response_model=list[PaymentLinkRead])
async def list_links(
    current_user: CurrentUser,
    db: DbSession,
    skip: int = 0,
    limit: int = 50,
):
    links = (
        db.query(PaymentLink)
        .filter(PaymentLink.user_id == current_user.id)
        .order_by(desc(PaymentLink.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return links


@router.get("/{link_id}", response_model=PaymentLinkRead)
async def get_link(
    link_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    link = db.query(PaymentLink).filter(
        PaymentLink.id == link_id,
        PaymentLink.user_id == current_user.id,
    ).first()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link no encontrado",
        )

    return link


@router.patch("/{link_id}", response_model=PaymentLinkRead)
async def update_link(
    link_id: UUID,
    link_data: PaymentLinkUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    link = db.query(PaymentLink).filter(
        PaymentLink.id == link_id,
        PaymentLink.user_id == current_user.id,
    ).first()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link no encontrado",
        )

    update_data = link_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(link, field, value)

    db.commit()
    db.refresh(link)
    return link


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    link_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    link = db.query(PaymentLink).filter(
        PaymentLink.id == link_id,
        PaymentLink.user_id == current_user.id,
    ).first()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link no encontrado",
        )

    if link.status == PaymentLinkStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar un link ya pagado",
        )

    link.status = PaymentLinkStatus.CANCELLED
    db.commit()
