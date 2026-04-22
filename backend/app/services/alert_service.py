"""
Alert Service - create, retrieve, and manage HR security alerts
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from loguru import logger

from app.models.models import Alert, ViolationType, AlertSeverity, User
from app.core.config import settings


class AlertService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_alert(
        self,
        user_id: int,
        query: str,
        violation_type: ViolationType,
        severity: AlertSeverity,
        description: str,
    ) -> Alert:
        alert = Alert(
            user_id=user_id,
            query=query,
            violation_type=violation_type,
            severity=severity,
            description=description,
        )
        self.db.add(alert)
        await self.db.flush()
        logger.warning(f"Alert created: user={user_id} type={violation_type} severity={severity}")

        # Trigger immediate WhatsApp for critical/high severity
        if settings.HIGH_SEVERITY_ALERT_IMMEDIATE and severity in (AlertSeverity.HIGH, AlertSeverity.CRITICAL):
            await self._trigger_immediate_alert(alert, user_id)

        # Check if user has exceeded violation threshold
        await self._check_violation_threshold(user_id)

        return alert

    async def _trigger_immediate_alert(self, alert: Alert, user_id: int):
        """Immediately notify employer via WhatsApp for high-severity alerts"""
        try:
            from app.services.whatsapp_service import WhatsAppService
            wa = WhatsAppService()
            result = await self.db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            email = user.email if user else "unknown"

            msg = (
                f"🚨 *IMMEDIATE HR ALERT*\n\n"
                f"Severity: {alert.severity.upper()}\n"
                f"Type: {alert.violation_type}\n"
                f"User: {email} (ID: {user_id})\n"
                f"Details: {alert.description}\n\n"
                f"Time: {alert.created_at.strftime('%Y-%m-%d %H:%M UTC')}"
            )
            await wa.send_message(msg)
        except Exception as e:
            logger.error(f"Immediate alert WhatsApp failed: {e}")

    async def _check_violation_threshold(self, user_id: int):
        """Check if user has exceeded daily violation threshold"""
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        result = await self.db.execute(
            select(func.count(Alert.id)).where(
                and_(Alert.user_id == user_id, Alert.created_at >= since)
            )
        )
        count = result.scalar() or 0

        if count >= settings.VIOLATION_THRESHOLD_PER_USER:
            logger.warning(f"User {user_id} exceeded violation threshold ({count} violations)")
            # Create a critical threshold alert
            threshold_alert = Alert(
                user_id=user_id,
                query=f"Exceeded {settings.VIOLATION_THRESHOLD_PER_USER} violations in 24h",
                violation_type=ViolationType.EXCESSIVE_PROBING,
                severity=AlertSeverity.CRITICAL,
                description=f"User has {count} violations in last 24 hours. Possible security threat.",
            )
            self.db.add(threshold_alert)
            await self.db.flush()

    async def get_alerts(
        self,
        user_id: Optional[int] = None,
        hours: int = 24,
        severity: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = select(Alert).where(Alert.created_at >= since)

        if user_id:
            query = query.where(Alert.user_id == user_id)
        if severity:
            query = query.where(Alert.severity == severity)

        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        query = query.order_by(Alert.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        alerts = result.scalars().all()

        # Count by type and severity
        by_type = {}
        high_count = 0
        for a in alerts:
            t = a.violation_type.value if hasattr(a.violation_type, 'value') else str(a.violation_type)
            by_type[t] = by_type.get(t, 0) + 1
            if a.severity in (AlertSeverity.HIGH, AlertSeverity.CRITICAL):
                high_count += 1

        return {
            "total": total,
            "high_severity": high_count,
            "by_type": by_type,
            "alerts": alerts,
        }
