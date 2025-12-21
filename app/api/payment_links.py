from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbSession
from app.models.payment_link import PaymentLink, PaymentLinkStatus
from app.models.user import User
from app.schemas.payment_link import PaymentLinkCreate, PaymentLinkRead, PaymentLinkUpdate

router = APIRouter()


def get_user_link(db: Session, link_id: UUID, user: User) -> PaymentLink:
    """Get a payment link owned by the user, or raise 404."""
    link = db.query(PaymentLink).filter(
        PaymentLink.id == link_id,
        PaymentLink.user_id == user.id,
    ).first()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link no encontrado",
        )
    return link


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
    return get_user_link(db, link_id, current_user)


@router.patch("/{link_id}", response_model=PaymentLinkRead)
async def update_link(
    link_id: UUID,
    link_data: PaymentLinkUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    link = get_user_link(db, link_id, current_user)
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
    link = get_user_link(db, link_id, current_user)
    if link.status == PaymentLinkStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar un link ya pagado",
        )

    link.status = PaymentLinkStatus.CANCELLED
    db.commit()
