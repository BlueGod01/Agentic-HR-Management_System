"""
Employee API - profile, salary, leave endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.models import User, Employee, LeaveRequest, LeaveStatus
from app.schemas.schemas import (
    EmployeeProfileResponse, SalaryResponse, LeaveBalanceResponse,
    LeaveRequestCreate, LeaveRequestResponse
)
from app.core.dependencies import get_current_employee
from datetime import datetime, timezone

router = APIRouter(prefix="/employee", tags=["Employee"])


async def _get_employee(user: User, db: AsyncSession) -> Employee:
    result = await db.execute(
        select(Employee).where(Employee.user_id == user.id, Employee.is_active == True)
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee record not found")
    return emp


@router.get("/profile", response_model=EmployeeProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    emp = await _get_employee(current_user, db)
    return emp


@router.get("/salary", response_model=SalaryResponse)
async def get_salary(
    current_user: User = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    emp = await _get_employee(current_user, db)
    return SalaryResponse(
        basic_salary=emp.basic_salary,
        hra=emp.hra,
        other_allowances=emp.other_allowances,
        deductions=emp.deductions,
        gross_salary=emp.gross_salary,
        net_salary=emp.net_salary,
    )


@router.get("/leave/balance", response_model=LeaveBalanceResponse)
async def get_leave_balance(
    current_user: User = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    emp = await _get_employee(current_user, db)
    return LeaveBalanceResponse(
        total_leave_days=emp.total_leave_days,
        used_leave_days=emp.used_leave_days,
        remaining_leave=emp.remaining_leave,
    )


@router.post("/leave/request", response_model=LeaveRequestResponse)
async def request_leave(
    payload: LeaveRequestCreate,
    current_user: User = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    emp = await _get_employee(current_user, db)

    if payload.start_date >= payload.end_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    leave = LeaveRequest(
        employee_id=emp.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        status=LeaveStatus.PENDING,
    )
    db.add(leave)
    await db.flush()
    return leave


@router.get("/leave/requests", response_model=list[LeaveRequestResponse])
async def get_my_leave_requests(
    current_user: User = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    emp = await _get_employee(current_user, db)
    result = await db.execute(
        select(LeaveRequest)
        .where(LeaveRequest.employee_id == emp.id)
        .order_by(LeaveRequest.requested_at.desc())
        .limit(20)
    )
    return result.scalars().all()
