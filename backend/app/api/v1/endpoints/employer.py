"""
Employer API - alerts, email management, WhatsApp webhook, user management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.db.database import get_db
from app.models.models import User, Employee, EmailDraft, EmailStatus, LeaveRequest, LeaveStatus
from app.schemas.schemas import (
    AlertSummaryResponse, AlertResponse,
    EmailGenerateRequest, EmailDraftResponse, EmailApprovalRequest,
    WhatsAppMessageRequest, UserCreateRequest
)
from app.core.dependencies import get_current_employer, get_current_admin
from app.core.security import hash_password
from app.services.alert_service import AlertService
from app.services.email_service import EmailService
from app.services.whatsapp_service import WhatsAppService
from app.agents.employer_agent import EmployerAgent
from loguru import logger

router = APIRouter(prefix="/employer", tags=["Employer"])


# ── Alerts ────────────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=AlertSummaryResponse)
async def get_alerts(
    hours: int = Query(24, ge=1, le=720),
    severity: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    alert_service = AlertService(db)
    data = await alert_service.get_alerts(hours=hours, severity=severity, page=page, page_size=page_size)
    return AlertSummaryResponse(**data)


@router.get("/alerts/summary")
async def get_alert_summary_text(
    hours: int = Query(24, ge=1, le=168),
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI-powered alert summary text"""
    agent = EmployerAgent(db)
    summary = await agent.generate_daily_alert_summary(hours=hours)
    return {"summary": summary, "hours": hours}


# ── Email Management ──────────────────────────────────────────────────────────

@router.post("/email/generate", response_model=EmailDraftResponse)
async def generate_email(
    payload: EmailGenerateRequest,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    """Generate an AI email draft for employer review"""
    agent = EmployerAgent(db)
    draft = await agent.generate_email_draft(
        recipient_email=payload.recipient_email,
        recipient_name=payload.recipient_name,
        subject_hint=payload.subject_hint,
        body_instruction=payload.body_instruction,
    )
    return draft


@router.get("/email/drafts", response_model=list[EmailDraftResponse])
async def list_email_drafts(
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EmailDraft)
        .order_by(EmailDraft.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.post("/email/approve")
async def approve_email(
    payload: EmailApprovalRequest,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    """Approve, edit, or reject an email draft"""
    result = await db.execute(select(EmailDraft).where(EmailDraft.id == payload.draft_id))
    draft = result.scalar_one_or_none()

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if payload.action == "approve":
        if payload.edited_body:
            draft.body = payload.edited_body
        if payload.edited_subject:
            draft.subject = payload.edited_subject
        draft.status = EmailStatus.APPROVED

        email_service = EmailService()
        sent = await email_service.send_approved_draft(db, draft.id)
        return {"status": "sent" if sent else "approved_not_sent", "draft_id": draft.id}

    elif payload.action == "reject":
        draft.status = EmailStatus.REJECTED
        return {"status": "rejected", "draft_id": draft.id}

    elif payload.action == "edit":
        if payload.edited_body:
            draft.body = payload.edited_body
        if payload.edited_subject:
            draft.subject = payload.edited_subject
        return {"status": "updated", "draft_id": draft.id}

    raise HTTPException(status_code=400, detail="Invalid action")


# ── WhatsApp ──────────────────────────────────────────────────────────────────

@router.post("/whatsapp/send")
async def send_whatsapp(
    payload: WhatsAppMessageRequest,
    current_user: User = Depends(get_current_employer),
):
    wa = WhatsAppService()
    sent = await wa.send_message(payload.message)
    return {"sent": sent}


@router.post("/whatsapp/webhook")
async def whatsapp_webhook(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook called by Green API when employer sends a message.
    Parses natural language commands and responds intelligently.
    """
    try:
        message_data = body.get("body", {})
        message_type = message_data.get("typeWebhook", "")

        if message_type != "incomingMessageReceived":
            return {"status": "ignored"}

        text = message_data.get("messageData", {}).get("textMessageData", {}).get("textMessage", "")
        if not text:
            return {"status": "no_text"}

        agent = EmployerAgent(db)
        parsed = await agent.parse_employer_command(text)
        intent = parsed.get("intent", "unknown")

        wa = WhatsAppService()

        if intent == "get_alerts":
            summary = await agent.generate_daily_alert_summary(hours=24)
            await wa.send_message(summary)
            return {"status": "alert_summary_sent"}

        elif intent == "send_email":
            employee_id_hint = parsed.get("employee_identifier")
            if employee_id_hint:
                result = await db.execute(
                    select(User).join(Employee).where(
                        (Employee.employee_code == employee_id_hint) |
                        (User.email == employee_id_hint)
                    )
                )
                target_user = result.scalar_one_or_none()
                if target_user:
                    draft = await agent.generate_email_draft(
                        recipient_email=target_user.email,
                        recipient_name=target_user.employee.full_name if target_user.employee else "Employee",
                        subject_hint=parsed.get("email_subject", "HR Communication"),
                        body_instruction=parsed.get("email_instruction", text),
                    )
                    preview = f"📧 *Email Draft Created*\n\nTo: {target_user.email}\nSubject: {draft.subject}\n\nReply 'approve {draft.id}' to send."
                    await wa.send_message(preview)
                    return {"status": "draft_sent_for_approval"}

            await wa.send_message("❓ I couldn't find the employee. Please provide a valid employee code or email.")
            return {"status": "employee_not_found"}

        else:
            await wa.send_message(
                "👋 *HR System Commands*\n\n"
                "• 'alerts' - Get today's alert summary\n"
                "• 'send email to [emp_code] about [topic]' - Draft an email\n"
            )
            return {"status": "help_sent"}

    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}")
        return {"status": "error", "detail": str(e)}


# ── User & Employee Management ────────────────────────────────────────────────

@router.post("/users/create", status_code=status.HTTP_201_CREATED)
async def create_employee_user(
    payload: UserCreateRequest,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    """Create a new employee user account"""
    from app.models.models import UserRole

    # Check unique email
    existing = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create User
    role = UserRole(payload.role)
    new_user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        role=role,
    )
    db.add(new_user)
    await db.flush()

    # Create Employee record
    new_emp = Employee(
        user_id=new_user.id,
        employee_code=payload.employee_code,
        full_name=payload.full_name,
        department=payload.department,
        designation=payload.designation,
        date_of_joining=payload.date_of_joining,
        basic_salary=payload.basic_salary,
        hra=payload.hra,
        other_allowances=payload.other_allowances,
        deductions=payload.deductions,
        phone=payload.phone,
    )
    db.add(new_emp)
    await db.flush()

    return {"user_id": new_user.id, "employee_id": new_emp.id, "email": new_user.email}


@router.get("/employees")
async def list_employees(
    department: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    query = select(Employee).where(Employee.is_active == True)
    if department:
        query = query.where(Employee.department == department)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    employees = result.scalars().all()
    return [
        {
            "id": e.id,
            "employee_code": e.employee_code,
            "full_name": e.full_name,
            "department": e.department,
            "designation": e.designation,
            "is_active": e.is_active,
        }
        for e in employees
    ]


@router.patch("/leave/{leave_id}/review")
async def review_leave_request(
    leave_id: int,
    action: str = Query(..., pattern="^(approve|reject)$"),
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LeaveRequest).where(LeaveRequest.id == leave_id))
    leave = result.scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")

    leave.status = LeaveStatus.APPROVED if action == "approve" else LeaveStatus.REJECTED
    leave.reviewed_at = datetime.now(timezone.utc)

    if action == "approve":
        emp_result = await db.execute(select(Employee).where(Employee.id == leave.employee_id))
        emp = emp_result.scalar_one_or_none()
        if emp:
            from datetime import timedelta
            days = (leave.end_date - leave.start_date).days + 1
            emp.used_leave_days += days

    await db.flush()
    return {"status": leave.status.value, "leave_id": leave_id}
