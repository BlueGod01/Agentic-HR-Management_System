"""
Email Service using aiosmtplib with Jinja2 templates
"""
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
import aiosmtplib
from jinja2 import Template
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.models import EmailDraft, EmailStatus


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>
  body { font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 20px; }
  .container { background: white; max-width: 600px; margin: auto; padding: 30px; border-radius: 8px; }
  .header { background: #1a1a2e; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }
  .content { padding: 20px 0; color: #333; line-height: 1.6; }
  .footer { margin-top: 30px; padding-top: 15px; border-top: 1px solid #eee; font-size: 12px; color: #888; text-align: center; }
</style></head>
<body>
<div class="container">
  <div class="header"><h2>{{ company_name }}</h2></div>
  <div class="content">{{ body | replace('\n', '<br>') }}</div>
  <div class="footer">
    This is an automated message from {{ company_name }} HR System. 
    Sent on {{ sent_date }}.
  </div>
</div>
</body>
</html>
"""


class EmailService:

    @property
    def _is_configured(self) -> bool:
        return bool(settings.SMTP_USERNAME and settings.SMTP_PASSWORD and settings.SMTP_FROM_EMAIL)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = True,
    ) -> bool:
        if not self._is_configured:
            logger.warning("SMTP not configured — skipping email send")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email

        # Plain text version
        msg.attach(MIMEText(body, "plain"))

        if html:
            html_body = Template(HTML_TEMPLATE).render(
                company_name=settings.APP_NAME,
                body=body,
                sent_date=datetime.now().strftime("%d %B %Y"),
            )
            msg.attach(MIMEText(html_body, "html"))

        try:
            smtp = aiosmtplib.SMTP(
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                use_tls=False,
            )
            await smtp.connect()
            if settings.SMTP_TLS:
                await smtp.starttls()
            await smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            await smtp.send_message(msg)
            await smtp.quit()
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Email send failed to {to_email}: {e}")
            return False

    async def send_approved_draft(self, db: AsyncSession, draft_id: int) -> bool:
        """Send an approved email draft and update its status"""
        result = await db.execute(select(EmailDraft).where(EmailDraft.id == draft_id))
        draft = result.scalar_one_or_none()

        if not draft or draft.status != EmailStatus.APPROVED:
            logger.warning(f"Draft {draft_id} not found or not approved")
            return False

        success = await self.send_email(
            to_email=draft.recipient_email,
            subject=draft.subject,
            body=draft.body,
        )

        if success:
            draft.status = EmailStatus.SENT
            draft.sent_at = datetime.now(timezone.utc)
            await db.flush()

        return success
