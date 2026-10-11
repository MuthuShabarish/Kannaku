# KANAKKU (கணக்கு) — Deployment & Operations Guide

## 1. Environments Overview

| Environment | Database | Frontend Serving | Backend Serving | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Local Dev (Zero-Docker)** | SQLite 3.50+ (`kanakku_dev.db`) | Vite Dev Server (`localhost:5173`) | Uvicorn reload (`localhost:8000`) | Fast feedback loop, zero external services needed. |
| **Local Dev (Dockerized)** | PostgreSQL 16 (`docker-compose`) | Vite Dev Server (`localhost:5173`) | Uvicorn in Docker (`localhost:8000`) | Tests full PostgreSQL features & constraints. |
| **Production** | Managed PostgreSQL 16 (AWS RDS / Supabase / Neon) | Nginx / Cloudflare Pages (Static PWA) | Gunicorn + Uvicorn workers | Strict SSL, daily automated WAL backups, zero downtime. |

---

## 2. Zero-Docker Quickstart (Immediate Development)

For development on developer machines (Windows, macOS, Linux) without Docker:

### 2.1. Backend Setup
```powershell
# Navigate to backend
cd backend

# Create and activate Python virtual environment
python -m venv .venv
.venv\Scripts\activate   # On Windows
# source .venv/bin/activate  # On Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Run database migrations (or auto-create models in dev mode)
alembic upgrade head

# Start API server
uvicorn app.main:app --reload --port 8000
```
Backend API interactive docs: `http://localhost:8000/docs`

### 2.2. Frontend Setup
```powershell
# In another terminal, navigate to frontend
cd frontend

# Install npm dependencies
npm install

# Start Vite development server
npm run dev
```
Frontend web application: `http://localhost:5173`

---

## 3. Docker Compose Setup (PostgreSQL Production Mirror)

### `docker-compose.yml` Specification:
```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: kanakku_postgres
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-kanakku}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-kanakku_secret_123}
      POSTGRES_DB: ${POSTGRES_DB:-kanakku_prod}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: kanakku_backend
    restart: always
    environment:
      DATABASE_URL: postgresql+psycopg://kanakku:kanakku_secret_123@db:5432/kanakku_prod
      SECRET_KEY: ${SECRET_KEY:-changeme_prod_secret_key_32_chars}
      ENVIRONMENT: production
    ports:
      - "8000:8000"
    depends_on:
      - db

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: kanakku_frontend
    restart: always
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

---

## 4. Environment Variables Configuration

Copy `.env.example` to `.env`:

```ini
# Application
ENVIRONMENT=development
APP_NAME=Kanakku
DEBUG=True

# Database (Leave as sqlite for zero-docker local dev, or provide postgres url)
DATABASE_URL=sqlite:///./kanakku_dev.db
# DATABASE_URL=postgresql+psycopg://kanakku:kanakku_secret_123@localhost:5432/kanakku_prod

# Security
SECRET_KEY=dev_secret_key_change_in_production_min_32_chars
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# CORS
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# AI Configuration (Optional - Core billing works 100% without AI)
AI_PROVIDER=gemini
AI_API_KEY=
AI_MODEL_NAME=gemini-1.5-flash
```

---

## 5. Database Backup & Disaster Recovery

1. **Automated Logical Backup**:
   ```bash
   pg_dump -U kanakku -h db -Fc kanakku_prod > /backups/kanakku_$(date +%Y%m%d_%H%M%S).dump
   ```
2. **Point-In-Time Recovery (PITR)**:
   - In production cloud providers, enable Continuous Archiving and Write-Ahead Log (WAL) archiving to restore the database to any exact minute prior to an incident.
3. **Database Restore**:
   ```bash
   pg_restore -U kanakku -h db -d kanakku_prod /backups/kanakku_backup.dump
   ```
