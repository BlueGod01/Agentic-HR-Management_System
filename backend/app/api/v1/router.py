"""
API v1 Router - combines all endpoint routers
"""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, chat, employee, employer

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(employee.router)
api_router.include_router(employer.router)
