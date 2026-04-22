"""
Pydantic v2 schemas for API request/response validation
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    user_id: int


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Employee ──────────────────────────────────────────────────────────────────

class EmployeeProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    full_name: str
    department: str
    designation: str
    date_of_joining: datetime
    is_active: bool


class SalaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    basic_salary: float
    hra: float
    other_allowances: float
    deductions: float
    gross_salary: float
    net_salary: float


class LeaveBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_leave_days: int
    used_leave_days: int
    remaining_leave: int


class LeaveRequestCreate(BaseModel):
    start_date: datetime
    end_date: datetime
    reason: str = Field(..., min_length=10, max_length=500)


class LeaveRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    start_date: datetime
    end_date: datetime
    reason: str
    status: str
    requested_at: datetime


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., min_length=1, max_length=100)


class ChatMessageResponse(BaseModel):
    session_id: str
    response: str
    tool_used: Optional[str] = None
    violation_detected: bool = False


class ChatHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    message: str
    created_at: datetime


# ── Alerts ────────────────────────────────────────────────────────────────────

class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    query: str
    violation_type: str
    severity: str
    description: str
    is_notified: bool
    created_at: datetime


class AlertSummaryResponse(BaseModel):
    total_alerts: int
    high_severity: int
    by_type: dict
    alerts: List[AlertResponse]


# ── Email ─────────────────────────────────────────────────────────────────────

class EmailGenerateRequest(BaseModel):
    recipient_email: EmailStr
    recipient_name: str
    subject_hint: str = Field(..., min_length=5, max_length=200)
    body_instruction: str = Field(..., min_length=10, max_length=1000)


class EmailDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_email: str
    subject: str
    body: str
    status: str
    created_at: datetime


class EmailApprovalRequest(BaseModel):
    draft_id: int
    action: str = Field(..., pattern="^(approve|reject|edit)$")
    edited_body: Optional[str] = None
    edited_subject: Optional[str] = None


# ── WhatsApp ──────────────────────────────────────────────────────────────────

class WhatsAppMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)


# ── User Management (Admin/Employer) ─────────────────────────────────────────

class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = Field(default="employee", pattern="^(employee|employer|admin)$")
    full_name: str
    employee_code: str
    department: str
    designation: str
    date_of_joining: datetime
    basic_salary: float = Field(ge=0)
    hra: float = Field(ge=0, default=0)
    other_allowances: float = Field(ge=0, default=0)
    deductions: float = Field(ge=0, default=0)
    phone: Optional[str] = None


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list
