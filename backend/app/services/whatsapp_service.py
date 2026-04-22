"""
WhatsApp Service using Green API
"""
import httpx
from loguru import logger
from app.core.config import settings


class WhatsAppService:

    def __init__(self):
        self.instance_id = settings.GREEN_API_INSTANCE_ID
        self.token = settings.GREEN_API_TOKEN
        self.base_url = settings.GREEN_API_BASE_URL
        self.employer_number = settings.EMPLOYER_WHATSAPP_NUMBER

    @property
    def _is_configured(self) -> bool:
        return bool(self.instance_id and self.token and self.employer_number)

    async def send_message(self, message: str, phone_number: str = None) -> bool:
        """Send WhatsApp message to employer or specified number"""
        if not self._is_configured:
            logger.warning("WhatsApp not configured — skipping send")
            return False

        number = phone_number or self.employer_number
        # Green API requires chatId format: {number}@c.us
        chat_id = f"{number}@c.us"

        url = f"{self.base_url}/waInstance{self.instance_id}/sendMessage/{self.token}"
        payload = {"chatId": chat_id, "message": message}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                logger.info(f"WhatsApp sent: idMessage={data.get('idMessage')}")
                return True
        except httpx.HTTPStatusError as e:
            logger.error(f"WhatsApp HTTP error: {e.response.status_code} — {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"WhatsApp send failed: {e}")
            return False

    async def receive_message(self, instance_id: str, token: str) -> list:
        """Receive incoming messages (for employer commands via webhook)"""
        url = f"{self.base_url}/waInstance{instance_id}/receiveNotification/{token}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200 and resp.content:
                    return [resp.json()]
                return []
        except Exception as e:
            logger.error(f"WhatsApp receive failed: {e}")
            return []

    async def delete_notification(self, receipt_id: int) -> bool:
        """Delete a processed notification"""
        url = f"{self.base_url}/waInstance{self.instance_id}/deleteNotification/{self.token}/{receipt_id}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(url)
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"WhatsApp delete notification failed: {e}")
            return False
