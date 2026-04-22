"""
Chat API - Employee HR Agent endpoint
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.models import User, Employee, ChatLog
from app.schemas.schemas import ChatMessageRequest, ChatMessageResponse, ChatHistoryItem
from app.core.dependencies import get_current_employee
from app.agents.employee_agent import EmployeeHRAgent
from loguru import logger

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    payload: ChatMessageRequest,
    current_user: User = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    # Get the employee record for this user
    result = await db.execute(
        select(Employee).where(Employee.user_id == current_user.id, Employee.is_active == True)
    )
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(status_code=404, detail="Employee record not found")

    # Log user message
    user_log = ChatLog(
        user_id=current_user.id,
        session_id=payload.session_id,
        role="user",
        message=payload.message,
    )
    db.add(user_log)

    try:
        # Run the LangGraph agent
        agent = EmployeeHRAgent(db=db, employee_id=employee.id, user_id=current_user.id)
        result_data = await agent.run(
            user_message=payload.message,
            session_id=payload.session_id,
        )
    except Exception as e:
        logger.error(f"Agent error for user {current_user.id}: {e}")
        result_data = {
            "response": "I'm experiencing technical difficulties. Please try again later.",
            "tool_used": None,
            "violation_detected": False,
        }

    # Log assistant response
    assistant_log = ChatLog(
        user_id=current_user.id,
        session_id=payload.session_id,
        role="assistant",
        message=result_data["response"],
        tool_used=result_data.get("tool_used"),
    )
    db.add(assistant_log)
    await db.flush()

    return ChatMessageResponse(
        session_id=payload.session_id,
        response=result_data["response"],
        tool_used=result_data.get("tool_used"),
        violation_detected=result_data.get("violation_detected", False),
    )


@router.get("/history/{session_id}", response_model=list[ChatHistoryItem])
async def get_history(
    session_id: str,
    current_user: User = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatLog)
        .where(ChatLog.user_id == current_user.id, ChatLog.session_id == session_id)
        .order_by(ChatLog.created_at.asc())
    )
    logs = result.scalars().all()
    return logs


@router.get("/sessions")
async def get_sessions(
    current_user: User = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    """Get list of chat sessions for current user"""
    from sqlalchemy import distinct, func
    result = await db.execute(
        select(ChatLog.session_id, func.max(ChatLog.created_at).label("last_active"))
        .where(ChatLog.user_id == current_user.id)
        .group_by(ChatLog.session_id)
        .order_by(func.max(ChatLog.created_at).desc())
        .limit(20)
    )
    sessions = result.all()
    return [{"session_id": s.session_id, "last_active": s.last_active} for s in sessions]
