from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys

from app.config import get_settings


class WebpayService:
    def __init__(self):
        settings = get_settings()

        if settings.webpay_environment == "integration":
            self.tx = Transaction(
                WebpayOptions(
                    commerce_code=IntegrationCommerceCodes.WEBPAY_PLUS,
                    api_key=IntegrationApiKeys.WEBPAY,
                )
            )
        else:
            self.tx = Transaction(
                WebpayOptions(
                    commerce_code=settings.webpay_commerce_code,
                    api_key=settings.webpay_api_key,
                )
            )

    def create_transaction(
        self,
        buy_order: str,
        session_id: str,
        amount: int,
        return_url: str,
    ) -> dict:
        response = self.tx.create(
            buy_order=buy_order,
            session_id=session_id,
            amount=amount,
            return_url=return_url,
        )
        # SDK v5 devuelve dict
        if isinstance(response, dict):
            return {"token": response["token"], "url": response["url"]}
        return {"token": response.token, "url": response.url}

    def commit_transaction(self, token: str) -> dict:
        response = self.tx.commit(token)
        # SDK v5 devuelve dict
        if isinstance(response, dict):
            return {
                "vci": response.get("vci"),
                "amount": response.get("amount"),
                "status": response.get("status"),
                "buy_order": response.get("buy_order"),
                "session_id": response.get("session_id"),
                "card_detail": response.get("card_detail", {}),
                "accounting_date": response.get("accounting_date"),
                "transaction_date": response.get("transaction_date"),
                "authorization_code": response.get("authorization_code"),
                "payment_type_code": response.get("payment_type_code"),
                "response_code": response.get("response_code"),
                "installments_number": response.get("installments_number"),
            }
        return {
            "vci": response.vci,
            "amount": response.amount,
            "status": response.status,
            "buy_order": response.buy_order,
            "session_id": response.session_id,
            "card_detail": response.card_detail,
            "accounting_date": response.accounting_date,
            "transaction_date": response.transaction_date,
            "authorization_code": response.authorization_code,
            "payment_type_code": response.payment_type_code,
            "response_code": response.response_code,
            "installments_number": response.installments_number,
        }

    def is_approved(self, commit_response: dict) -> bool:
        return (
            commit_response.get("response_code") == 0
            and commit_response.get("status") == "AUTHORIZED"
        )


webpay_service = WebpayService()
