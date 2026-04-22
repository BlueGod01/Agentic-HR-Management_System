"""
Test suite - Auth and Chat endpoints
Run: pytest tests/ -v
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.main import app
from app.db.database import get_db, Base
from app.db.seed import seed_database

TEST_DB_URL = "sqlite+aiosqlite:///./test_hr.db"

engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as db:
        await seed_database(db)
        await db.commit()
    app.dependency_overrides[get_db] = override_get_db
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    import os
    if os.path.exists("./test_hr.db"):
        os.remove("./test_hr.db")


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def employee_token(client):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "alice.johnson@company.com",
        "password": "Alice@123"
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def employer_token(client):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "employer@company.com",
        "password": "Employer@123"
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


# ── Auth Tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_login_success(client):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "alice.johnson@company.com",
        "password": "Alice@123"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "employee"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "alice.johnson@company.com",
        "password": "wrongpassword"
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nobody@company.com",
        "password": "password123"
    })
    assert resp.status_code == 401


# ── Employee Endpoint Tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_my_profile(client, employee_token):
    resp = await client.get("/api/v1/employee/profile", headers={"Authorization": f"Bearer {employee_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Alice Johnson"
    assert data["department"] == "Engineering"


@pytest.mark.asyncio
async def test_get_my_salary(client, employee_token):
    resp = await client.get("/api/v1/employee/salary", headers={"Authorization": f"Bearer {employee_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "basic_salary" in data
    assert "net_salary" in data
    assert data["net_salary"] > 0


@pytest.mark.asyncio
async def test_get_leave_balance(client, employee_token):
    resp = await client.get("/api/v1/employee/leave/balance", headers={"Authorization": f"Bearer {employee_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "remaining_leave" in data
    assert data["total_leave_days"] == 24


@pytest.mark.asyncio
async def test_employee_cannot_access_employer_routes(client, employee_token):
    resp = await client.get("/api/v1/employer/alerts", headers={"Authorization": f"Bearer {employee_token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_access_blocked(client):
    resp = await client.get("/api/v1/employee/profile")
    assert resp.status_code == 403


# ── Employer Endpoint Tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_employer_get_alerts(client, employer_token):
    resp = await client.get("/api/v1/employer/alerts", headers={"Authorization": f"Bearer {employer_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "alerts" in data


@pytest.mark.asyncio
async def test_employer_list_employees(client, employer_token):
    resp = await client.get("/api/v1/employer/employees", headers={"Authorization": f"Bearer {employer_token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 3
