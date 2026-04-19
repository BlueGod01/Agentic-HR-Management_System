# =========================================
# FULLY DEPLOYABLE AGENTIC HR SYSTEM
# FastAPI + LangGraph + PostgreSQL + Green API (WhatsApp)
# =========================================

import os
import json
import psycopg2
import requests
from fastapi import FastAPI, Request
from typing import TypedDict, Optional
from langgraph.graph import StateGraph

# =========================================
# CONFIG
# =========================================

DB_CONFIG = {
    "host": "localhost",
    "database": "hr_db",
    "user": "readonly_user",
    "password": "secure_password"
}

GREEN_API_URL = "https://api.green-api.com"
GREEN_INSTANCE_ID = "your_instance_id"
GREEN_TOKEN = "your_token"

SMTP_USER = "your_email@gmail.com"
SMTP_PASS = "app_password"

# =========================================
# FASTAPI INIT
# =========================================

app = FastAPI()

# =========================================
# LLM (REPLACE WITH GEMINI)
# =========================================

class LLM:
    def invoke(self, prompt: str):
        return f"[LLM OUTPUT]\n{prompt[:200]}"

llm = LLM()

# =========================================
# STATE
# =========================================

class AgentState(TypedDict):
    user_input: str
    intent: Optional[str]
    sql_result: Optional[str]
    email_draft: Optional[str]
    email_approved: Optional[bool]
    policy_response: Optional[str]
    final_output: Optional[str]

# =========================================
# DB CONNECTION
# =========================================

def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_session(readonly=True, autocommit=True)
    return conn

# =========================================
# SQL AGENT
# =========================================

def sql_agent(state: AgentState):
    prompt = f"Convert to safe SELECT SQL: {state['user_input']}"
    query = llm.invoke(prompt)

    if not query.lower().startswith("select"):
        state["final_output"] = "Blocked unsafe query"
        return state

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        state["sql_result"] = str(rows)
        state["final_output"] = state["sql_result"]
    except Exception as e:
        state["final_output"] = str(e)

    return state

# =========================================
# POLICY AGENT
# =========================================

def policy_agent(state: AgentState):
    context = "Policy docs..."
    prompt = f"Answer from policy: {state['user_input']} Context: {context}"
    state["policy_response"] = llm.invoke(prompt)
    state["final_output"] = state["policy_response"]
    return state

# =========================================
# EMAIL AGENT
# =========================================

def email_agent(state: AgentState):
    prompt = f"Write HR email: {state['user_input']}"
    state["email_draft"] = llm.invoke(prompt)
    return state

# =========================================
# STORE DRAFT FOR APPROVAL
# =========================================

def store_email_for_approval(draft):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("INSERT INTO email_queue (draft, approved) VALUES (%s, %s) RETURNING id", (draft, False))
    email_id = cur.fetchone()[0]
    conn.commit()
    return email_id

# =========================================
# SEND WHATSAPP MESSAGE
# =========================================

def send_whatsapp(message, phone):
    url = f"{GREEN_API_URL}/waInstance{GREEN_INSTANCE_ID}/sendMessage/{GREEN_TOKEN}"
    payload = {
        "chatId": f"{phone}@c.us",
        "message": message
    }
    requests.post(url, json=payload)

# =========================================
# EMAIL SENDER
# =========================================

import smtplib
from email.mime.text import MIMEText

def send_email(draft):
    msg = MIMEText(draft)
    msg["Subject"] = "HR Notification"
    msg["From"] = SMTP_USER
    msg["To"] = "employee@example.com"

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)

# =========================================
# INTENT CLASSIFIER
# =========================================

def classify(state: AgentState):
    text = state["user_input"].lower()
    if "email" in text:
        state["intent"] = "email"
    elif "policy" in text:
        state["intent"] = "policy"
    else:
        state["intent"] = "sql"
    return state

# =========================================
# ORCHESTRATOR
# =========================================

def orchestrator(state: AgentState):
    if state["intent"] == "email":
        state = email_agent(state)
        email_id = store_email_for_approval(state["email_draft"])

        send_whatsapp(
            f"Approve email ID {email_id}? Reply YES {email_id} or NO {email_id}",
            "91XXXXXXXXXX"
        )

        state["final_output"] = "Email sent for approval via WhatsApp"

    elif state["intent"] == "policy":
        state = policy_agent(state)

    else:
        state = sql_agent(state)

    return state

# =========================================
# GRAPH
# =========================================

def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("classify", classify)
    graph.add_node("orchestrator", orchestrator)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "orchestrator")

    return graph.compile()

agent = build_graph()

# =========================================
# WHATSAPP WEBHOOK
# =========================================

@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()

    message = data.get("messageData", {}).get("textMessageData", {}).get("textMessage")
    sender = data.get("senderData", {}).get("sender")

    if message:
        if message.startswith("YES"):
            email_id = message.split()[1]
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute("SELECT draft FROM email_queue WHERE id=%s", (email_id,))
            draft = cur.fetchone()[0]

            send_email(draft)

            cur.execute("UPDATE email_queue SET approved=true WHERE id=%s", (email_id,))
            conn.commit()

            send_whatsapp("Email sent successfully", sender)

        else:
            result = agent.invoke({"user_input": message})
            send_whatsapp(result.get("final_output", "Done"), sender)

    return {"status": "ok"}

# =========================================
# DB SCHEMA (RUN MANUALLY)
# =========================================

"""
CREATE TABLE email_queue (
    id SERIAL PRIMARY KEY,
    draft TEXT,
    approved BOOLEAN DEFAULT FALSE
);
"""
