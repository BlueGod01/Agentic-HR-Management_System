"""
Employer Agent - handles email generation and alert summarization via Gemini
"""
import json
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.models.models import Alert, EmailDraft, User, Employee, EmailStatus, AlertSeverity


def get_llm():
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.3,
        max_output_tokens=2048,
        convert_system_message_to_human=True,
    )


class EmployerAgent:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm()

    # ── Email Generation ──────────────────────────────────────────────────────

    async def generate_email_draft(
        self,
        recipient_email: str,
        recipient_name: str,
        subject_hint: str,
        body_instruction: str,
    ) -> EmailDraft:
        """Generate a professional email draft using Gemini"""

        prompt = f"""You are a professional HR communication specialist.
Generate a formal, professional email based on the instructions below.

Recipient: {recipient_name} ({recipient_email})
Subject Hint: {subject_hint}
Instruction: {body_instruction}

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{{
  "subject": "email subject here",
  "body": "full email body here with proper greeting, content, and sign-off"
}}"""

        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content if isinstance(response.content, str) else str(response.content)

        # Clean JSON
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        try:
            parsed = json.loads(content)
            subject = parsed.get("subject", subject_hint)
            body = parsed.get("body", "")
        except json.JSONDecodeError:
            logger.warning("LLM did not return valid JSON for email, using fallback")
            subject = subject_hint
            body = content

        draft = EmailDraft(
            recipient_email=recipient_email,
            subject=subject,
            body=body,
            status=EmailStatus.PENDING_APPROVAL,
            triggered_by="employer",
        )
        self.db.add(draft)
        await self.db.flush()
        return draft

    # ── Alert Summarization ───────────────────────────────────────────────────

    async def generate_daily_alert_summary(self, hours: int = 24) -> str:
        """Generate a human-readable summary of today's alerts using Gemini"""

        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await self.db.execute(
            select(Alert, User).join(User).where(Alert.created_at >= since)
        )
        rows = result.all()

        if not rows:
            return "✅ No violations or alerts in the last 24 hours. All clear!"

        alert_data = []
        for alert, user in rows:
            alert_data.append(
                f"- User ID {user.id} ({user.email}): [{alert.severity.upper()}] "
                f"{alert.violation_type} — {alert.description}"
            )

        alerts_text = "\n".join(alert_data)
        prompt = f"""You are an HR security system. Summarize these alerts for the employer in a clear, actionable WhatsApp message.
Be concise. Use emojis sparingly. Maximum 300 words.

Alerts from the last {hours} hours:
{alerts_text}

Write the summary now:"""

        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        summary = response.content if isinstance(response.content, str) else str(response.content)

        # Mark alerts as notified
        for alert, _ in rows:
            alert.is_notified = True
        await self.db.flush()

        return f"📊 *HR Alert Summary — Last {hours}h*\n\n{summary}"

    # ── WhatsApp Command Parsing ──────────────────────────────────────────────

    async def parse_employer_command(self, message: str) -> dict:
        """Parse natural language command from employer via WhatsApp"""

        prompt = f"""You are an HR system command parser. Parse the employer's command and return JSON.

Command: "{message}"

Return ONLY valid JSON with this structure:
{{
  "intent": "send_email | get_alerts | get_employee_info | unknown",
  "employee_identifier": "employee code or email if mentioned, else null",
  "email_subject": "subject if email intent, else null",
  "email_instruction": "what the email should say if email intent, else null"
}}"""

        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content if isinstance(response.content, str) else str(response.content)
        content = content.strip().strip("```json").strip("```").strip()

        try:
            return json.loads(content)
        except Exception:
            return {"intent": "unknown", "employee_identifier": None, "email_subject": None, "email_instruction": None}
