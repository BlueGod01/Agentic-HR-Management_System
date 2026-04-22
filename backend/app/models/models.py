"""
SQLAlchemy ORM Models
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    String, Integer, Float, Boolean, Text, DateTime,
    ForeignKey, Enum as SAEnum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.db.database import Base


def utcnow():
    return datetime.now(timezone.utc)


# ── Enums ─────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    EMPLOYEE = "employee"
    EMPLOYER = "employer"
    ADMIN = "admin"


class ViolationType(str, enum.Enum):
    UNAUTHORIZED_DATA_ACCESS = "unauthorized_data_access"
    EXCESSIVE_PROBING = "excessive_probing"
    POLICY_VIOLATION = "policy_violation"
    SUSPICIOUS_QUERY = "suspicious_query"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EmailStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    REJECTED = "rejected"


class LeaveStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ── User (Auth) ───────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.EMPLOYEE)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    employee: Mapped[Optional["Employee"]] = relationship("Employee", back_populates="user", uselist=False)
    chat_logs: Mapped[list["ChatLog"]] = relationship("ChatLog", back_populates="user")
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="user")


# ── Employee ──────────────────────────────────────────────────────────────────

class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    employee_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_joining: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Salary (encrypted at rest in production via DB-level encryption)
    basic_salary: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    hra: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    other_allowances: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    deductions: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    @property
    def gross_salary(self) -> float:
        return self.basic_salary + self.hra + self.other_allowances

    @property
    def net_salary(self) -> float:
        return self.gross_salary - self.deductions

    # Leave
    total_leave_days: Mapped[int] = mapped_column(Integer, default=24)
    used_leave_days: Mapped[int] = mapped_column(Integer, default=0)

    @property
    def remaining_leave(self) -> int:
        return self.total_leave_days - self.used_leave_days

    manager_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship("User", back_populates="employee")
    leave_requests: Mapped[list["LeaveRequest"]] = relationship("LeaveRequest", back_populates="employee")


# ── Leave Request ─────────────────────────────────────────────────────────────

class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[LeaveStatus] = mapped_column(SAEnum(LeaveStatus), default=LeaveStatus.PENDING)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="leave_requests")


# ── Chat Log ──────────────────────────────────────────────────────────────────

class ChatLog(Base):
    __tablename__ = "chat_logs"
    __table_args__ = (Index("ix_chat_logs_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant
    message: Mapped[str] = mapped_column(Text, nullable=False)
    tool_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship("User", back_populates="chat_logs")


# ── Alert ─────────────────────────────────────────────────────────────────────

class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alerts_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    violation_type: Mapped[ViolationType] = mapped_column(SAEnum(ViolationType))
    severity: Mapped[AlertSeverity] = mapped_column(SAEnum(AlertSeverity), default=AlertSeverity.MEDIUM)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship("User", back_populates="alerts")


# ── Email Draft ───────────────────────────────────────────────────────────────

class EmailDraft(Base):
    __tablename__ = "email_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipient_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[EmailStatus] = mapped_column(SAEnum(EmailStatus), default=EmailStatus.DRAFT)
    triggered_by: Mapped[str] = mapped_column(String(100), default="employer")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ── Policy Document ───────────────────────────────────────────────────────────

class PolicyDocument(Base):
    __tablename__ = "policy_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
