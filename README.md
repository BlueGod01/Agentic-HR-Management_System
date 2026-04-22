# 🧠 Agentic AI HR System

A production-ready, secure, and scalable **Agentic AI-powered HR assistant** built with FastAPI, LangGraph, Google Gemini, React, and Docker.

![Python](https://img.shields.io/badge/python-3.11%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green) ![LangGraph](https://img.shields.io/badge/LangGraph-Agent-orange) ![React](https://img.shields.io/badge/React-20%2B-blueviolet) ![Google Gemini](https://img.shields.io/badge/Gemini_1.5-Flash-yellow) ![Docker](https://img.shields.io/badge/Docker-Production-blue)

## Why This Project

Traditional HR systems often require employees to navigate complex portals to access simple information—such as leave balances or company policies—while placing a significant burden on HR teams to handle repetitive queries. This project addresses these inefficiencies by automating routine HR operations through a robust agentic workflow.

The system enables employees to securely interact with an AI assistant to retrieve personalized information, including profile details, salary data, and organizational policies. At the same time, it empowers employers with automated daily alerts and seamless WhatsApp integration, enabling efficient monitoring and management of operations.

Employers can interact with the system via both a web dashboard and WhatsApp. Through conversational commands on WhatsApp, they can generate email drafts, log employee violations, and query company policies. All generated emails are presented as drafts for review and approval before being sent, ensuring accuracy and control. The system also supports bulk communication, allowing employers to send messages to multiple employees in a single step directly from WhatsApp.

In addition, the agentic system integrates directly with the company’s employee database, enabling dynamic data retrieval and intelligent decision-making. It can process user-defined queries and execute data-driven workflows at scale. For example, an employer can instruct the system to identify employees who have taken more than five sick leaves within a given month and automatically generate warning emails for review, significantly reducing manual effort and operational overhead.

Security and data governance are integral to the system. It ensures that all data is accessible only to authorized personnel, with strict role-based access control (RBAC) in place. Employee data remains restricted to the respective employee and authorized employer roles, ensuring privacy, security, and compliance.

## Tech Stack

| Layer | Technology |
|---|---|
| User Interface | React, Vite |
| API & Backend | FastAPI, Python 3.11+ |
| Orchestration | LangGraph, LangChain |
| LLM Provider | Google Gemini Models (1.5 Flash / Pro) |
| Database | SQLite (Dev) / PostgreSQL (Prod), SQLAlchemy |
| External APIs | Green API (WhatsApp), SMTP (Email) |
| Deployment | Docker, NGINX |

## Architecture

<img width="32000" height="115250" alt="hr_system_architecture_all" src="https://github.com/user-attachments/assets/63364cfd-2aaf-4e7c-84a7-c2354b00bb98" />


## How It Works

The system operates across distinct workflows, ensuring strict role-based access and data isolation.

### 1. Employee Workflow (LangGraph Agent)
The employee agent uses **tool-based LangGraph** powered by Google Gemini:
- **ReAct Loop**: The AI processes the user's message, checks the system prompt (which injects security rules), and decides which tools to call.
- **Available Tools**: `get_my_profile()`, `get_my_salary()`, `get_my_leave_balance()`, `search_policy(query)`, `log_violation(description)`.
- **Safety**: The agent refuses unauthorized queries. If an employee tries to access another's data, a violation is logged, and a WhatsApp alert is triggered for critical issues.

### 2. Employer Workflow (Dashboard & WhatsApp)
- **Web Dashboard**: Employers have a dedicated dashboard to manage employees and view alerts.
- **WhatsApp Integration**: Using Green API, employers can receive AI-generated daily summaries or send commands directly via WhatsApp (e.g., "send email to EMP001 about leave rejection")
- **Email-Automation**: Employers can ask to send emails to employees. The LLM agent will write an email based on the query and ask for approval before sending it.

### 3. Security Architecture
- **Auth**: JWT (access & refresh tokens) and bcrypt password hashing.
- **Access Control**: Role-based (Employee, Employer, Admin) with data isolation (Employees only see their own data).
- **Network Security**: NGINX rate limiting on API and chat endpoints, with the database accessible only via backend APIs (never directly by the LLM).

## 💰 Cost Estimation (1,000 Requests/Month)

This architecture leverages Google's **Gemini 1.5 Flash** for tool-calling and reasoning, offering excellent performance at a minimal cost.

**Assumptions per HR Request:**
- **Agentic Loop (avg. 2 iterations per turn)**: ReAct loops increase token usage as the model thinks, calls a tool, and observes the result. Estimated ~3,000 input tokens, ~500 output tokens per interaction.
- **Total per request**: ~3,000 input tokens, ~500 output tokens.

**Option A: Gemini 1.5 Flash (Default & Highly Recommended)**
- Input Cost: ~$0.075 per 1M tokens
- Output Cost: ~$0.30 per 1M tokens
- **Estimated Monthly Cost (1,000 requests):** **~$0.38 / month**

**Option B: Gemini 1.5 Pro (For extreme reasoning depth)**
- Input Cost: ~$1.25 per 1M tokens
- Output Cost: ~$5.00 per 1M tokens
- **Estimated Monthly Cost (1,000 requests):** **~$6.25 / month**

> *Conclusion: By utilizing Gemini 1.5 Flash, hosting a secure, multi-tool agentic HR assistant becomes incredibly cost-effective, easily scaling to thousands of interactions for less than a dollar.*

## ⚠️ Limitations

- **WhatsApp API Restrictions**: The Green API integration requires scanning a QR code with a physical WhatsApp device and maintaining active connectivity. Unofficial WhatsApp APIs may face rate limits or temporary bans if message volume is exceedingly high.
- **Email Rate Limits**: Standard Gmail SMTP (used in this project) is limited to 500 emails per day. For enterprise-scale deployments, a dedicated service like SendGrid or AWS SES is required.

## 🚀 Future Improvements (Roadmap)

- [ ] **Multi-tenant SaaS Support**: Allow multiple companies to use the system in isolated environments.
- [ ] **Vector Database Integration**: Add FAISS or Pinecone to support semantic search over large corporate policy documents.
- [ ] **Slack / Teams Integration**: Expand chatbot accessibility beyond the web UI to popular corporate messaging apps.
- [ ] **Voice-enabled Assistant**: Support voice commands and responses for accessibility and ease of use.
- [ ] **Advanced Analytics**: Interactive dashboards for HR teams to visualize employee sentiment and query trends.

## Project Structure

```text
hr-ai-system/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/     # Route handlers (auth, chat, employee, employer)
│   │   ├── agents/               # LangGraph HR agents (employee, employer)
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── services/             # Alert, email, WhatsApp services
│   │   └── core/                 # Config, security, scheduler
│   ├── migrations/               # Alembic database migrations
│   ├── tests/                    # Pytest test suite
│   ├── requirements.txt          # Python dependencies
│   └── Dockerfile                # Backend Docker image
├── frontend/
│   └── src/
│       ├── pages/                # React UI components (Login, Chat, Dashboard)
│       └── store/                # Zustand state management
├── docker/
│   └── nginx.conf                # NGINX reverse proxy & rate limiting
├── docker-compose.yml            # Multi-container orchestration
├── scripts/                      # Setup, start, and deploy bash scripts
└── .env.example                  # Environment variable template
```

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

### 1. Clone & Setup
```bash
git clone <your-repo-url>
cd hr-ai-system
bash scripts/setup_dev.sh
```

### 2. Environment Variables
Copy the template and configure your keys:
```bash
cp .env.example .env
```
**Essential Variables in `.env`:**
```env
# REQUIRED:
APP_SECRET_KEY=your_random_32_char_secret
JWT_SECRET_KEY=your_random_32_char_secret
GOOGLE_API_KEY=your_gemini_api_key_here
DATABASE_URL=sqlite:///./sql_app.db # Dev default

# OPTIONAL (WhatsApp):
GREEN_API_INSTANCE_ID=your_instance_id
GREEN_API_TOKEN=your_token
EMPLOYER_WHATSAPP_NUMBER=91XXXXXXXXXX

# OPTIONAL (Email):
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
SMTP_FROM_EMAIL=your_email@gmail.com
```

### 3. Run Development Servers
```bash
bash scripts/start_dev.sh
```

| Service | URL |
|---|---|
| Employee UI | http://localhost:5173 |
| API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

### 4. Demo Credentials (auto-seeded)
| Role | Email | Password |
|---|---|---|
| Employee | alice.johnson@company.com | Alice@123 |
| Employer | employer@company.com | Employer@123 |
| Admin | admin@company.com | Admin@123 |

## 🐳 Production Deployment

```bash
# 1. Configure production .env (Set APP_ENV=production, update DATABASE_URL to PostgreSQL)
cp .env.example .env

# 2. Deploy using Docker Compose
bash scripts/deploy_docker.sh

# 3. Monitor Logs
docker compose logs -f backend
```

## 🔄 Useful Commands

**Run Tests:**
```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

**Database Migrations (Alembic):**
```bash
cd backend
source venv/bin/activate
alembic revision --autogenerate -m "describe_your_change"
alembic upgrade head
```

## 📄 License

MIT License - See LICENSE file for details.
