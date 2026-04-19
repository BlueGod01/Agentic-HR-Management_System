# =========================================
# EMPLOYEE WORKFLOW
# =========================================

import os
import re
import psycopg2
import smtplib
from email.mime.text import MIMEText
from typing import TypedDict, Optional
from fastapi import FastAPI, Request, HTTPException, Depends
from langgraph.graph import StateGraph

# =========================================
# ENV / CONFIG (use .env in real deployment)
# =========================================

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "hr_db"),
    "user": os.getenv("DB_USER", "readonly_user"),
    "password": os.getenv("DB_PASS", "secure_password"),
}

SMTP_USER = os.getenv("SMTP_USER", "no-reply@company.com")
SMTP_PASS = os.getenv("SMTP_PASS", "app_password")
EMPLOYER_EMAIL = os.getenv("EMPLOYER_EMAIL", "employer@company.com")

# =========================================
# APP
# =========================================

app = FastAPI(title="Employee Agentic HR API")

# =========================================
# LLM (MOCK - replace with Gemini)
# =========================================

class LLM:
    def invoke(self, prompt: str) -> str:
        return f"[LLM]\n{prompt[:300]}"

llm = LLM()

# =========================================
# DB (READ-ONLY + RLS via SET LOCAL)
# =========================================

def get_db_conn(employee_id: int):
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor()
    # Set session variable for RLS (must be used in DB policies)
    cur.execute("SET LOCAL app.current_employee_id = %s", (employee_id,))
    return conn

# =========================================
# AUTH (MOCK)
# Replace with JWT validation in production
# =========================================

def get_current_employee(req: Request) -> int:
    emp = req.headers.get("x-employee-id")
    if not emp:
        raise HTTPException(401, "Missing employee id")
    return int(emp)

# =========================================
# STATE
# =========================================

class State(TypedDict):
    user_input: str
    employee_id: int
    intent: Optional[str]
    sql_result: Optional[str]
    email_draft: Optional[str]
    email_to: Optional[str]
    policy_ok: Optional[bool]
    policy_notes: Optional[str]
    alert: Optional[str]
    final_output: Optional[str]

# =========================================
# INTENT CLASSIFIER
# =========================================

def classify(state: State) -> State:
    t = state["user_input"].lower()
    if any(k in t for k in ["email", "mail", "send"]):
        state["intent"] = "email"
    elif any(k in t for k in ["policy", "rule", "allowed"]):
        state["intent"] = "policy"
    else:
        state["intent"] = "sql"
    return state

# =========================================
# SQL AGENT (EMPLOYEE-SCOPED ONLY)
# =========================================

ALLOWED_TABLES = {"employees", "leaves", "payroll"}


def _sanitize_select(query: str) -> bool:
    q = query.strip().lower()
    if not q.startswith("select"):
        return False
    # basic blocklist
    banned = [";", "--", "/*", "insert", "update", "delete", "drop", "alter"]
    return not any(b in q for b in banned)


def sql_agent(state: State) -> State:
    prompt = f"""
You are a SQL generator. Create a SAFE SELECT query for PostgreSQL.
Rules:
- ONLY SELECT
- Must filter by employee_id = {state['employee_id']}
- Use tables among: employees, leaves, payroll
- No joins unless necessary

User request: {state['user_input']}
"""
    query = llm.invoke(prompt)

    if not _sanitize_select(query):
        state["final_output"] = "Request blocked for safety."
        return state

    # enforce employee_id filter if missing
    if f"employee_id = {state['employee_id']}" not in query:
        # naive enforcement
        if "where" in query.lower():
            query += f" AND employee_id = {state['employee_id']}"
        else:
            query += f" WHERE employee_id = {state['employee_id']}"

    try:
        conn = get_db_conn(state["employee_id"]) 
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        state["sql_result"] = str(rows)
        state["final_output"] = state["sql_result"]
    except Exception as e:
        state["final_output"] = f"DB error: {e}"

    return state

# =========================================
# POLICY AUDITOR (RAG MOCK)
# =========================================

VIOLATION_PATTERNS = [
    r"other employee",
    r"all employees",
    r"highest salary",
]


def policy_agent(state: State) -> State:
    # Mock retrieval
    context = "Company policies: employees can access only their own data; emailing allowed only to employer."

    # simple violation detection
    text = state["user_input"].lower()
    violates = any(re.search(p, text) for p in VIOLATION_PATTERNS)

    if violates:
        state["policy_ok"] = False
        state["policy_notes"] = "Attempted restricted access."
        state["alert"] = f"Employee {state['employee_id']} violation: {state['user_input']}"
        state["final_output"] = "This request violates company policy and has been reported."
        return state

    # normal answer grounded in policy
    ans = llm.invoke(f"Answer using policy only.\nContext: {context}\nQ: {state['user_input']}")
    state["policy_ok"] = True
    state["policy_notes"] = ans
    state["final_output"] = ans
    return state

# =========================================
# EMAIL AGENT (EMPLOYEE → EMPLOYER ONLY)
# =========================================


def extract_email_target(text: str) -> Optional[str]:
    # naive extraction
    m = re.search(r"to\s+([\w\.-]+@[\w\.-]+)", text.lower())
    return m.group(1) if m else None


def email_agent(state: State) -> State:
    to = extract_email_target(state["user_input"]) or EMPLOYER_EMAIL

    # enforce rule: employee can only email employer
    if to.lower() != EMPLOYER_EMAIL.lower():
        state["final_output"] = "Employees can only send emails to the employer."
        state["alert"] = f"Employee {state['employee_id']} tried emailing non-employer: {to}"
        return state

    prompt = f"""
Write a concise professional email from employee {state['employee_id']} to employer.
Instruction: {state['user_input']}
Include Subject and Body.
"""
    draft = llm.invoke(prompt)

    state["email_to"] = EMPLOYER_EMAIL
    state["email_draft"] = draft
    state["final_output"] = draft
    return state

# =========================================
# EMAIL SEND (FROM EMPLOYEE ADDRESS - MOCK mapping)
# =========================================


def send_email(from_addr: str, to_addr: str, body: str):
    msg = MIMEText(body)
    msg["Subject"] = "Employee Message"
    msg["From"] = from_addr
    msg["To"] = to_addr

    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

# =========================================
# ORCHESTRATOR
# =========================================


def orchestrator(state: State) -> State:
    # Always run policy audit first
    state = policy_agent(state)

    if state.get("policy_ok") is False:
        return state

    if state["intent"] == "email":
        state = email_agent(state)
        if state.get("email_draft"):
            # send immediately (employee initiated). In production, optionally require confirmation UI.
            from_addr = f"employee{state['employee_id']}@company.com"  # mapping placeholder
            send_email(from_addr, state["email_to"], state["email_draft"])
            state["final_output"] = "Email sent to employer."
        return state

    if state["intent"] == "policy":
        return state  # already answered

    # default SQL
    state = sql_agent(state)
    return state

# =========================================
# GRAPH
# =========================================


def build_graph():
    g = StateGraph(State)
    g.add_node("classify", classify)
    g.add_node("orchestrator", orchestrator)
    g.set_entry_point("classify")
    g.add_edge("classify", "orchestrator")
    return g.compile()

agent = build_graph()

# =========================================
# ALERT LOG (WRITE via separate RW user in real prod)
# =========================================


def log_alert(alert: str):
    # In production, use a separate write-enabled service/role
    try:
        conn = psycopg2.connect(host=DB_CONFIG["host"], database=DB_CONFIG["database"], user=os.getenv("DB_RW_USER", "rw_user"), password=os.getenv("DB_RW_PASS", "rw_pass"))
        cur = conn.cursor()
        cur.execute("INSERT INTO alerts(message) VALUES (%s)", (alert,))
        conn.commit()
        conn.close()
    except Exception:
        pass

# =========================================
# API ENDPOINT
# =========================================

@app.post("/employee/chat")
async def employee_chat(req: Request, employee_id: int = Depends(get_current_employee)):
    data = await req.json()
    text = data.get("message")
    if not text:
        raise HTTPException(400, "message required")

    state: State = {"user_input": text, "employee_id": employee_id}
    result = agent.invoke(state)

    if result.get("alert"):
        log_alert(result["alert"])

    return {"response": result.get("final_output")}

# =========================================
# DB SCHEMA (RUN MANUALLY)
# =========================================

"""
-- Enable RLS
ALTER TABLE employees ENABLE ROW LEVEL SECURITY;
ALTER TABLE leaves ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll ENABLE ROW LEVEL SECURITY;

-- Example policy using session var
CREATE POLICY emp_isolation_employees ON employees
USING (employee_id = current_setting('app.current_employee_id')::int);

CREATE POLICY emp_isolation_leaves ON leaves
USING (employee_id = current_setting('app.current_employee_id')::int);

CREATE POLICY emp_isolation_payroll ON payroll
USING (employee_id = current_setting('app.current_employee_id')::int);

-- Alerts table (write via RW role)
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
