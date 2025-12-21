import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import get_settings


async def send_payment_notification(
    recipient_email: str,
    description: str,
    amount: int,
    authorization_code: str,
):
    settings = get_settings()

    if not settings.smtp_user or not settings.smtp_password:
        print(f"[Email] Notificación de pago (SMTP no configurado):")
        print(f"  Para: {recipient_email}")
        print(f"  Descripción: {description}")
        print(f"  Monto: ${amount:,}")
        print(f"  Código: {authorization_code}")
        return

    message = MIMEMultipart("alternative")
    message["Subject"] = f"Pago recibido: {description}"
    message["From"] = settings.email_from
    message["To"] = recipient_email

    formatted_amount = f"${amount:,.0f}".replace(",", ".")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #10B981; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
            .amount {{ font-size: 32px; font-weight: bold; color: #10B981; }}
            .detail {{ margin: 10px 0; padding: 10px; background: white; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Pago Recibido</h1>
            </div>
            <div class="content">
                <p class="amount">{formatted_amount} CLP</p>
                <div class="detail">
                    <strong>Descripción:</strong> {description}
                </div>
                <div class="detail">
                    <strong>Código de autorización:</strong> {authorization_code}
                </div>
                <p>El pago ha sido procesado exitosamente.</p>
            </div>
        </div>
    </body>
    </html>
    """

    message.attach(MIMEText(html, "html"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
    except Exception as e:
        print(f"[Email] Error enviando notificación: {e}")
