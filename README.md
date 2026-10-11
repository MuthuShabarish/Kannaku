# KANAKKU (கணக்கு)

> **Adaptive, Multilingual, AI-Assisted Business Management Platform**  
> *"Business software should adapt to the business owner, not force the owner to learn complicated software."*

---

## 🌟 Overview

**Kanakku (கணக்கு)** is an enterprise-grade, yet remarkably simple business platform engineered to serve businesses across their entire lifecycle:
1. **Kanakku Simple**: Tailored for solo shopkeepers, roadside stalls, and small retail counters (1–3 workers). High-contrast jumbo touch pad, 5-second quick billing, zero accounting jargon, and instant daily answers (Sales, Cash, Expenses, Low Stock, Estimated Profit).
2. **Kanakku Growth**: Designed for growing stores, workshops, and wholesale operations (4–10 workers). Comprehensive product variants, purchase orders, Moving Average Costing, customer credit ledgers (Udhar), staff roles, and optional manufacturing recipes (BOM).
3. **Kanakku Enterprise**: Architected for multi-branch and multi-warehouse operations. Role-based access control, purchase requisition approvals, consolidated vs branch P&L, immutable audit trails, and API integrations.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.11+ / 3.14, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, Pytest.
- **Frontend**: React 18, Vite, React Router v6, Tailwind CSS / Vanilla CSS tokens, i18n Localization Engine.
- **Database**: PostgreSQL 16 (Production / Docker) + SQLite 3.50+ (Zero-Docker Local Dev & Testing).
- **Languages**: Tamil (தமிழ்), Tanglish (Tamil in Latin script), and English.
- **AI Engine**: Controlled tool-calling with strict human-in-the-loop confirmation.

---

## 📚 Complete Project Documentation

All specifications, architectural designs, schemas, and operational guides are maintained in the [`docs/`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/Kanakku/docs/) directory:

- 📋 [**Product Specification**](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/Kanakku/docs/PRODUCT_SPEC.md) — Product vision, personas, 3 UI tiers, adaptive onboarding, language rules, and financial definitions.
- 🏗️ [**System Architecture**](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/Kanakku/docs/ARCHITECTURE.md) — Component diagrams, frontend and backend structures, tenant isolation, AI tool calling, and offline sync.
- 🗄️ [**Database Architecture**](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/Kanakku/docs/DATABASE.md) — Table schemas, `NUMERIC(14, 4)` precision, Moving Average Costing formulas, locking mechanisms, and indexes.
- 📊 [**Entity-Relationship (ER) Diagram**](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/Kanakku/docs/ER_DIAGRAM.md) — Mermaid visual diagram of all entities and relationships.
- 🔌 [**REST API Specification**](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/Kanakku/docs/API.md) — Endpoint catalog, authentication, request/response models, and status codes.
- 🛡️ [**Security & Privacy**](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/Kanakku/docs/SECURITY.md) — Password hashing, JWT lifecycle, RBAC rules, data isolation, and AI sandboxing.
- 🧪 [**Testing Strategy**](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/Kanakku/docs/TESTING.md) — Pytest suite, financial math unit tests, tenant isolation checks, and critical E2E test journeys.
- 🚀 [**Deployment & Operations**](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/Kanakku/docs/DEPLOYMENT.md) — Zero-Docker quickstart, Docker Compose setup, environment variables, backup & recovery.
- 🧠 [**Architectural Decision Records (ADRs)**](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/Kanakku/docs/DECISIONS.md) — Tradeoff rationale for monorepo, frameworks, database dual-engine, and decimal currency.
- 🗺️ [**Implementation Plan & Roadmap**](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/Kanakku/docs/IMPLEMENTATION_PLAN.md) — Dependency-aware 10-stage execution plan and acceptance criteria.
- 📈 [**Progress Tracker**](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/Kanakku/docs/PROGRESS.md) — Current stage status, executed test logs, and next steps.

---

## ⚡ Quickstart

### 1. Prerequisites Check
Ensure Python 3.11+ and Node.js v18+ are installed. (Docker is optional for local development).

### 2. Backend Startup (Local Zero-Docker Mode)
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Interactive API Documentation will be available at: `http://localhost:8000/docs`

### 3. Frontend Startup
```powershell
cd frontend
npm install
npm run dev
```
Application will be accessible at: `http://localhost:5173`

---

## 📍 Current Status

- **Stage 0 (Planning & Architecture)**: **COMPLETED** ✅
- **Stage 1 (Core Foundation, Multi-Tenant Engine & Auth)**: **READY TO START** ⏳
