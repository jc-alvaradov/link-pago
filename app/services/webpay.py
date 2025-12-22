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
        # SDK v5 returns dict, normalize to dict for consistency
        if not isinstance(response, dict):
            response = response.__dict__

        fields = [
            "vci", "amount", "status", "buy_order", "session_id",
            "accounting_date", "transaction_date", "authorization_code",
            "payment_type_code", "response_code", "installments_number",
        ]
        result = {field: response.get(field) for field in fields}
        result["card_detail"] = response.get("card_detail", {})
        return result

    def is_approved(self, commit_response: dict) -> bool:
        return (
            commit_response.get("response_code") == 0
            and commit_response.get("status") == "AUTHORIZED"
        )


webpay_service = WebpayService()
