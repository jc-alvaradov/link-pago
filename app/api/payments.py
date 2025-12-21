import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.payment_link import PaymentLink, PaymentLinkStatus
from app.models.transaction import Transaction, TransactionStatus
from app.services.email import send_payment_notification
from app.services.webpay import webpay_service

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def generate_buy_order() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_part = uuid.uuid4().hex[:8]
    return f"{timestamp}{random_part}"[:26]


# IMPORTANTE: /return debe estar ANTES de /{slug} para que no sea capturado como slug
@router.get("/return", response_class=HTMLResponse)
async def payment_return(
    request: Request,
    background_tasks: BackgroundTasks,
    token_ws: str | None = None,
    TBK_TOKEN: str | None = None,
    TBK_ID_SESION: str | None = None,
    TBK_ORDEN_COMPRA: str | None = None,
    db: Session = Depends(get_db),
):
    # Case 1: Normal flow - has token_ws
    if token_ws and not TBK_TOKEN:
        transaction = db.query(Transaction).filter(Transaction.token == token_ws).first()

        if not transaction:
            return templates.TemplateResponse(
                "payment_error.html",
                {"request": request, "error": "Transacción no encontrada"},
            )

        try:
            commit_response = webpay_service.commit_transaction(token_ws)
        except Exception as e:
            logger.error(f"Webpay commit failed for token {token_ws}: {e}")
            transaction.status = TransactionStatus.FAILED
            db.commit()
            return templates.TemplateResponse(
                "payment_error.html",
                {"request": request, "error": "Error al confirmar el pago. Por favor intente nuevamente."},
            )

        transaction.webpay_response = commit_response
        transaction.response_code = commit_response.get("response_code")
        transaction.authorization_code = commit_response.get("authorization_code")
        transaction.payment_type_code = commit_response.get("payment_type_code")
        transaction.installments_number = commit_response.get("installments_number")

        card_detail = commit_response.get("card_detail", {})
        if card_detail:
            transaction.card_last_four = card_detail.get("card_number")

        if webpay_service.is_approved(commit_response):
            transaction.status = TransactionStatus.AUTHORIZED
            transaction.authorized_at = datetime.now(timezone.utc)

            link = transaction.payment_link
            link.times_paid += 1

            # Solo marcar como PAID si es single_use
            if link.single_use:
                link.status = PaymentLinkStatus.PAID

            db.commit()

            background_tasks.add_task(
                send_payment_notification,
                link.user.email,
                link.description,
                link.amount,
                transaction.authorization_code,
            )

            return templates.TemplateResponse(
                "payment_success.html",
                {
                    "request": request,
                    "amount": f"${transaction.amount:,.0f}".replace(",", "."),
                    "authorization_code": transaction.authorization_code,
                    "card_last_four": transaction.card_last_four,
                    "description": link.description,
                },
            )
        else:
            transaction.status = TransactionStatus.FAILED
            db.commit()
            return templates.TemplateResponse(
                "payment_error.html",
                {"request": request, "error": "Pago rechazado por el banco"},
            )

    # Case 2: User aborted payment
    if TBK_TOKEN:
        transaction = db.query(Transaction).filter(
            Transaction.buy_order == TBK_ORDEN_COMPRA
        ).first()
        if transaction:
            transaction.status = TransactionStatus.FAILED
            db.commit()
        return templates.TemplateResponse(
            "payment_error.html",
            {"request": request, "error": "Pago cancelado por el usuario"},
        )

    # Case 3: Timeout
    if TBK_ID_SESION and TBK_ORDEN_COMPRA and not token_ws:
        transaction = db.query(Transaction).filter(
            Transaction.buy_order == TBK_ORDEN_COMPRA
        ).first()
        if transaction:
            transaction.status = TransactionStatus.FAILED
            db.commit()
        return templates.TemplateResponse(
            "payment_error.html",
            {"request": request, "error": "Tiempo de pago expirado"},
        )

    # Case 4: Unknown error
    return templates.TemplateResponse(
        "payment_error.html",
        {"request": request, "error": "Error procesando el pago"},
    )


@router.get("/{slug}", response_class=HTMLResponse)
async def payment_page(
    request: Request,
    slug: str,
    db: Session = Depends(get_db),
):
    link = db.query(PaymentLink).filter(PaymentLink.slug == slug).first()

    if not link:
        return templates.TemplateResponse(
            "payment_error.html",
            {"request": request, "error": "Link de pago no encontrado"},
            status_code=404,
        )

    if link.status == PaymentLinkStatus.PAID:
        return templates.TemplateResponse(
            "payment_error.html",
            {"request": request, "error": "Este link ya fue pagado"},
        )

    if link.status == PaymentLinkStatus.CANCELLED:
        return templates.TemplateResponse(
            "payment_error.html",
            {"request": request, "error": "Este link fue cancelado"},
        )

    if link.is_expired:
        return templates.TemplateResponse(
            "payment_error.html",
            {"request": request, "error": "Este link ha expirado"},
        )

    link.views_count += 1
    db.commit()

    return templates.TemplateResponse(
        "payment_page.html",
        {
            "request": request,
            "link": link,
            "formatted_amount": f"${link.amount:,.0f}".replace(",", "."),
        },
    )


@router.post("/{slug}/init")
async def init_payment(
    slug: str,
    db: Session = Depends(get_db),
):
    link = db.query(PaymentLink).filter(PaymentLink.slug == slug).first()

    if not link or not link.is_payable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link no disponible para pago",
        )

    buy_order = generate_buy_order()
    session_id = f"session_{uuid.uuid4().hex[:16]}"

    transaction = Transaction(
        payment_link_id=link.id,
        buy_order=buy_order,
        session_id=session_id,
        amount=link.amount,
    )
    db.add(transaction)
    db.commit()

    return_url = f"{settings.app_url}/pay/return"

    try:
        result = webpay_service.create_transaction(
            buy_order=buy_order,
            session_id=session_id,
            amount=link.amount,
            return_url=return_url,
        )
    except Exception as e:
        logger.error(f"Webpay create transaction failed for order {buy_order}: {e}")
        transaction.status = TransactionStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al iniciar la transacción. Por favor intente nuevamente.",
        )

    transaction.token = result["token"]
    db.commit()

    redirect_url = f"{result['url']}?token_ws={result['token']}"
    return {"redirect_url": redirect_url}
