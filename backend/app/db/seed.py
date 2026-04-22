"""
Database seeder - creates demo employer, employees, and policies on first run
"""
from datetime import datetime, timezone
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import User, Employee, UserRole, PolicyDocument
from app.core.security import hash_password


DEMO_POLICIES = [
    {
        "title": "Annual Leave Policy",
        "category": "Leave",
        "content": """Annual Leave Policy

All full-time employees are entitled to 24 days of paid annual leave per calendar year.
Leave must be applied for at least 3 days in advance except in emergencies.
Unused leave can be carried forward up to a maximum of 10 days to the next year.
Leave encashment is allowed for a maximum of 5 days per year.
Employees must get approval from their manager before taking leave.
Sick leave requires a medical certificate for absences longer than 2 consecutive days.
Maternity leave: 26 weeks for the first two children.
Paternity leave: 15 days.
""",
    },
    {
        "title": "Code of Conduct Policy",
        "category": "Conduct",
        "content": """Code of Conduct

All employees are expected to maintain professional behavior at all times.
Harassment of any kind — sexual, racial, or otherwise — is strictly prohibited.
Confidential company information must not be shared with external parties.
Use of company resources for personal gain is not permitted.
Employees must report conflicts of interest to HR immediately.
Social media usage during work hours should be limited to work-related activities.
Violations may result in disciplinary action up to and including termination.
""",
    },
    {
        "title": "Work From Home Policy",
        "category": "Remote Work",
        "content": """Work From Home Policy

Employees may work from home up to 2 days per week with manager approval.
Remote employees must be available during core hours: 10 AM to 4 PM local time.
A stable internet connection and a quiet workspace are required.
Attendance in team meetings is mandatory regardless of work location.
Equipment provided by the company must be used only for work purposes.
WFH days cannot be used during probation period.
""",
    },
    {
        "title": "Salary & Compensation Policy",
        "category": "Compensation",
        "content": """Salary and Compensation Policy

Salaries are disbursed on the last working day of each month.
All employees receive a payslip via email on the 25th of each month.
The CTC structure includes: Basic Salary, HRA, Special Allowances, and deductions such as PF and TDS.
Annual increments are based on performance appraisals conducted in Q1.
Bonuses are discretionary and subject to company performance.
Employees can raise salary queries with the HR department via the HR portal.
""",
    },
    {
        "title": "IT Security Policy",
        "category": "IT & Security",
        "content": """IT and Data Security Policy

Employees must not share passwords or access credentials with anyone.
Company laptops must have the approved antivirus software installed.
Sensitive data must not be stored on personal devices.
All data transfers outside the organization must be approved by IT.
Employees must report any suspected security breach to IT immediately.
Use of unauthorized software is prohibited on company machines.
Two-factor authentication is mandatory for all company accounts.
""",
    },
]


async def seed_database(db: AsyncSession) -> None:
    """Seed the database with demo data if not already seeded"""

    # Check if already seeded
    result = await db.execute(select(User).limit(1))
    if result.scalar_one_or_none():
        logger.info("Database already seeded — skipping")
        return

    logger.info("Seeding database with demo data...")

    # ── Create Employer account ───────────────────────────────────────────────
    employer_user = User(
        email="employer@company.com",
        hashed_password=hash_password("Employer@123"),
        role=UserRole.EMPLOYER,
    )
    db.add(employer_user)
    await db.flush()

    # ── Create Admin account ──────────────────────────────────────────────────
    admin_user = User(
        email="admin@company.com",
        hashed_password=hash_password("Admin@123"),
        role=UserRole.ADMIN,
    )
    db.add(admin_user)
    await db.flush()

    # ── Create Employee accounts ──────────────────────────────────────────────
    employees_data = [
        {
            "email": "alice.johnson@company.com",
            "password": "Alice@123",
            "code": "EMP001",
            "name": "Alice Johnson",
            "dept": "Engineering",
            "designation": "Senior Software Engineer",
            "doj": datetime(2021, 6, 1, tzinfo=timezone.utc),
            "basic": 80000, "hra": 32000, "allowances": 15000, "deductions": 12000,
            "leave_used": 5,
        },
        {
            "email": "bob.smith@company.com",
            "password": "Bob@123",
            "code": "EMP002",
            "name": "Bob Smith",
            "dept": "Marketing",
            "designation": "Marketing Manager",
            "doj": datetime(2020, 3, 15, tzinfo=timezone.utc),
            "basic": 70000, "hra": 28000, "allowances": 12000, "deductions": 10500,
            "leave_used": 8,
        },
        {
            "email": "carol.das@company.com",
            "password": "Carol@123",
            "code": "EMP003",
            "name": "Carol Das",
            "dept": "Finance",
            "designation": "Financial Analyst",
            "doj": datetime(2022, 9, 1, tzinfo=timezone.utc),
            "basic": 60000, "hra": 24000, "allowances": 10000, "deductions": 9000,
            "leave_used": 2,
        },
    ]

    for emp_data in employees_data:
        user = User(
            email=emp_data["email"],
            hashed_password=hash_password(emp_data["password"]),
            role=UserRole.EMPLOYEE,
        )
        db.add(user)
        await db.flush()

        emp = Employee(
            user_id=user.id,
            employee_code=emp_data["code"],
            full_name=emp_data["name"],
            department=emp_data["dept"],
            designation=emp_data["designation"],
            date_of_joining=emp_data["doj"],
            basic_salary=emp_data["basic"],
            hra=emp_data["hra"],
            other_allowances=emp_data["allowances"],
            deductions=emp_data["deductions"],
            used_leave_days=emp_data["leave_used"],
        )
        db.add(emp)

    # ── Create Policy Documents ───────────────────────────────────────────────
    for policy in DEMO_POLICIES:
        doc = PolicyDocument(
            title=policy["title"],
            category=policy["category"],
            content=policy["content"],
        )
        db.add(doc)

    await db.flush()
    logger.info("✅ Demo data seeded successfully!")
    logger.info("  Employer: employer@company.com / Employer@123")
    logger.info("  Admin:    admin@company.com    / Admin@123")
    logger.info("  Employees: alice.johnson@company.com / Alice@123")
    logger.info("             bob.smith@company.com     / Bob@123")
    logger.info("             carol.das@company.com     / Carol@123")
