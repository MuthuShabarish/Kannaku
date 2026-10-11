# KANAKKU (கணக்கு) — Architectural Decision Records (ADRs)

## ADR 001: Monorepo Project Structure
- **Status**: Accepted
- **Context**: Kanakku requires tight schema alignment between backend Pydantic models, frontend TypeScript/JavaScript interfaces, and unified documentation.
- **Decision**: Organize the project as a structured monorepo:
  - `backend/` — Python FastAPI API and data models.
  - `frontend/` — React Vite web application and PWA assets.
  - `docs/` — Living engineering and product documentation.
- **Consequence**: Streamlined version control, single issue/PR workflow, and effortless local full-stack startup.

---

## ADR 002: Backend Framework — FastAPI with SQLAlchemy 2.0
- **Status**: Accepted
- **Context**: We need high-performance asynchronous REST endpoints, automatic OpenAPI documentation, strict runtime validation, and robust relational ORM capabilities.
- **Decision**: Select **FastAPI** paired with **SQLAlchemy 2.0** and **Pydantic v2**.
- **Consequence**: Type-safe request/response handling, standardized schema serialization, and enterprise-grade transaction management.

---

## ADR 003: Monetary Precision, Currency Rules & Configurable Business Currency
- **Status**: Accepted
- **Context**: Standard floating-point IEEE 754 numbers produce unacceptable rounding drift (`0.1 + 0.2 = 0.30000000000000004`) in financial systems. The application must support India-first micro-merchants while accommodating international or multi-currency businesses.
- **Decision**:
  - Default currency is **Indian Rupee (₹ / INR)**.
  - Every business has a configurable currency (`currency_code`, `currency_symbol`).
  - Database schema uses `NUMERIC(14, 4)` for all currency and quantity fields in PostgreSQL.
  - Backend math strictly utilizes Python's `decimal.Decimal` with explicit context (`ROUND_HALF_EVEN`).
  - Explicit rounding rules:
    - Line item totals and tax calculations use Banker's Rounding (Round Half to Even) rounded to 2 decimal places.
    - Cash tender display supports business-level configuration (exact 2 decimal places, or round to nearest whole integer ₹1 for high-speed cash transactions).
- **Consequence**: Zero financial drift across tax, discount, unit cost, and ledger calculations.

---

## ADR 004: Primary Canonical Database — PostgreSQL 16+ with Integration Testing
- **Status**: Accepted
- **Context**: PostgreSQL is mandatory for reliable enterprise concurrency, row-level locking (`SELECT ... FOR UPDATE`), check constraints (`current_stock >= 0`), strict ACID transactions, and tenant isolation. While SQLite can be used offline for lightweight tests, it does not behave identically to PostgreSQL under concurrent load or strict relational operations.
- **Decision**:
  - **PostgreSQL 16+** is the canonical primary database for both development and production.
  - SQLite is treated strictly as an auxiliary, temporary fallback for lightweight unit tests, and is explicitly recognized as NOT behaviorally identical to PostgreSQL.
  - The CI and validation pipeline mandates dedicated PostgreSQL integration test execution covering:
    - Concurrent stock deductions (row-level locking vs race conditions).
    - Database check constraints and foreign key delete restrictions.
    - Strict tenant isolation across multi-tenant sessions.
- **Consequence**: Full transactional integrity and production fidelity guaranteed before deployment.

---

## ADR 005: Three Adaptive Experiences on a Unified Core
- **Status**: Accepted
- **Context**: Small shopkeepers find traditional ERPs completely unusable, while growing businesses find simple trackers too restrictive. Building three separate software products causes maintenance fragmentation.
- **Decision**:
  - Build **one shared data and API core**.
  - Expose three distinct frontend presentation layers:
    - **Simple**: 5-second billing, jumbo touch pad, 5 primary metrics, no jargon.
    - **Growth**: Multi-variant inventory, customer credit (Udhar), supplier dues, production batches.
    - **Enterprise**: Multi-branch selector, granular RBAC, purchase approvals, immutable audit logs.
- **Consequence**: A business can smoothly grow from a solo shop into an enterprise without data migration or changing software vendors.

---

## ADR 006: Multilingual & Tanglish Architecture
- **Status**: Accepted
- **Context**: Small shop owners in Tamil Nadu frequently communicate and read in Tamil or Tanglish (Tamil written in English characters) on messaging apps. English-only software severely impedes adoption.
- **Decision**:
  - Create centralized JSON translation dictionaries: `en.json`, `ta.json`, `tanglish.json`.
  - No user-facing strings hardcoded in UI components.
  - Provide a 1-tap language switcher visible on all screens.
  - Curate financial terms with domain experts rather than relying on automated machine translation.
- **Consequence**: Deep linguistic accessibility and comfort for shopkeepers with varied literacy levels.

---

## ADR 007: Safe AI Tool Calling with Human-in-the-Loop Confirmation
- **Status**: Accepted
- **Context**: Large Language Models can hallucinate, misunderstand ambiguous speech, or make unwarranted assumptions about prices and stock.
- **Decision**:
  - The AI assistant functions strictly via structured tool-calling.
  - AI outputs are treated as **untrusted candidate drafts**.
  - Sensitive operations (recording a sale, issuing a credit refund, altering stock) present an interactive preview card that requires explicit human confirmation.
  - Core billing and reporting remain 100% operational if AI APIs are offline.
- **Consequence**: High user productivity via voice/text assistance without any risk of AI-induced financial loss or data corruption.

---

## ADR 008: Immutable Financial Accounting & Reversals
- **Status**: Accepted
- **Context**: Modifying or deleting sales, purchases, or ledger entries opens severe loopholes for fraud, accidental data loss, and mismatched tax audits.
- **Decision**:
  - Completed transactions are append-only.
  - Invoices and payments cannot be deleted or mutated.
  - Errors must be corrected by creating a formal **Credit Note / Reversal Transaction** with an audit reason and timestamp.
- **Consequence**: Complete, audit-compliant financial trail.

---

## ADR 009: Phone-Based Authentication, PIN Security & Brute-Force Defenses
- **Status**: Accepted
- **Context**: Micro-business owners operate mobile-first and prefer phone number + numeric PIN/password over email-based workflows. However, short numeric PINs are susceptible to brute-force attacks if defensive controls are absent.
- **Decision**:
  - Canonical phone identity format: E.164 (`+91...`).
  - Hashing: Argon2id with unique salt. **Zero plaintext PIN or password storage/logging anywhere in the codebase or database**.
  - Rate Limiting: Dual-key rate limiting by both Client IP and Phone Number (5 failed attempts per 15 minutes triggers lockout and exponential backoff).
  - Session Security: Short-lived access token JWTs + rotating refresh tokens stored in HTTP-Only, Secure, SameSite=Strict cookies with token family reuse detection.
  - Account Recovery: Emergency recovery key provided at onboarding to prevent unauthorized takeover without compromising convenience.
- **Consequence**: High mobile-friendly ergonomics for shop owners without compromising security integrity.
