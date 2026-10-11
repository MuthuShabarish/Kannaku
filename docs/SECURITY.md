# KANAKKU (கணக்கு) — Security & Privacy Architecture

## 1. Authentication & Phone-Based Identity Security

Kanakku supports phone number-based authentication designed for small business operators, accompanied by banking-grade defensive controls:

### 1.1. Phone Number Format & Normalization
- All phone numbers are strictly parsed, validated, and normalized to the **E.164 international standard** (e.g., `+919876543210`) using a telephony validator before query execution or persistence.
- Prevents identity spoofing through alternate phone formatting (spaces, leading zeros, dashes).

### 1.2. Cryptographic PIN & Password Handling
- **Never Store or Log Plaintext Credentials**: Plaintext PINs and passwords must NEVER be stored in the database, included in logs, returned in API payloads, or exposed in error messages.
- **Argon2id Hashing**: PINs and passwords are cryptographically hashed using **Argon2id** (the winner of the Password Hashing Competition) with recommended parameters:
  - Memory cost: 65,536 KiB (64 MiB)
  - Time cost: 3 iterations
  - Parallelism: 4 lanes
  - Salt: Cryptographically secure random 16-byte salt per user.
- **PIN Entropy Requirements**: Numeric PINs must be at least 4–6 digits, prohibiting trivial sequences (e.g., `1234`, `0000`, repeated digits). Passwords for desktop/management users require a minimum of 8 characters with mixed character classes.

### 1.3. Rate Limiting & Brute-Force Defenses
To prevent brute-forcing short PINs:
- **Dual-Key Rate Limiting**: Rate limits are enforced on both `(IP Address)` and `(Phone Number)` keys simultaneously:
  - Max 5 failed login attempts per phone number within a rolling 15-minute window.
  - On the 5th failed attempt, the account enters a **temporary lockout state** for 15 minutes.
  - Subsequent failures trigger exponential backoff (30 min, 1 hr, 24 hr).
  - IP-based rate limiting caps requests to 20 attempts per minute across all endpoints to thwart distributed dictionary attacks.
- **Constant-Time Verification**: Password/PIN hash comparisons execute via constant-time functions (`secrets.compare_digest` / Argon2 verify) to eliminate side-channel timing attacks.

### 1.4. Session Security & Token Lifecycle
- **Dual-Token Architecture**:
  - **Access Token**: Short-lived (15–30 minutes) JWT containing claims: `sub` (User UUID), `biz` (Business UUID), `role`, `jti` (Token UUID), and `exp`.
  - **Refresh Token with Rotation (RTR)**: Long-lived (14–30 days) opaque cryptographically random string (256-bit entropy).
- **Token Family Invalidation**: Every refresh token issuance rotates the existing token. If a previously consumed refresh token is presented, the system detects a token theft event and **immediately invalidates all active sessions** for that user.
- **Cookie Security**: On web clients, refresh tokens are stored exclusively in `HTTP-Only`, `Secure`, `SameSite=Strict` cookies with path restriction to `/api/v1/auth/refresh`.

### 1.5. Account Recovery & Takeover Prevention
- **Staff Accounts**: Can only be reset by a verified business Owner or Manager through an authenticated management endpoint with audit logging.
- **Owner Account Recovery**:
  - **Emergency Recovery Key**: Generated at business onboarding; presented to the owner as a one-time 16-character alphanumeric recovery key (stored hashed with Argon2id in DB).
  - **Two-Step Verification**: If an owner forgets their PIN, recovery requires the emergency recovery key or secondary verified email/channel.
  - Prevents SIM-swap and unauthorized physical device access from compromising business financial records.

### 1.6. Route-Level Authorization & Tenant Boundary Enforcement
- Every private endpoint enforces two mandatory security dependencies:
  1. `get_current_user`: Validates JWT signature, checks `is_active == True`, and verifies session revocation status.
  2. `get_current_business`: Validates that the user has an active membership and role in the requested `business_id` (from header `X-Business-ID` or token claim).
- Role-based capabilities (e.g., `require_permission(Permission.VIEW_PROFIT)`) mask sensitive financial fields and endpoints from Cashier/Biller accounts.

---

## 2. Strict Business & Tenant Isolation

Tenant isolation is non-negotiable. Every database query that accesses business records must be scoped to the authenticated tenant:
1. **Dependency Injection Enforcement**:
   - `get_current_user` extracts and verifies the JWT.
   - `get_current_business` verifies that the user is an active member of the requested `business_id`.
2. **Repository Guardrails**:
   - All database queries explicitly filter by `where(Model.business_id == business.id)`.
   - Foreign key relations across businesses are structurally prevented.
3. **Role-Based Access Control (RBAC)**:
   - **Owner**: Full access across all branches, financial reports, settings, and staff configuration.
   - **Manager**: Inventory adjustments, purchase receipts, customer credit approvals, daily closing reports. Cannot delete business or alter subscription/owner details.
   - **Cashier / Biller**: Can create sales, view customer balances, record customer payments, record basic petty expenses. **Cannot view purchase costs, supplier margins, or overall profit/loss reports.**
   - **Auditor**: Read-only access to transactions, audit logs, and reports.

---

## 3. Financial Integrity & Immutability

1. **No Silent Record Mutability**:
   - Completed sales, purchase receipts, and recorded payments cannot be modified via `UPDATE` or deleted via `DELETE`.
   - Corrections must be processed through an explicit **Reversal / Credit Note** transaction, referencing the original invoice, recording the reason, user ID, and timestamp.
2. **Overselling & Concurrency Protection**:
   - Inventory decrements execute in atomic transactions.
   - Database level check constraint or query condition: `UPDATE inventory_balances SET current_stock = current_stock - :qty WHERE warehouse_id = :wid AND product_id = :pid AND current_stock >= :qty;`
   - If rows affected == 0, the transaction aborts with `INSUFFICIENT_STOCK`.
3. **Idempotency Controls**:
   - Offline or mobile transactions submit a `client_tx_id` (UUID v4).
   - The database enforces a `UNIQUE(business_id, client_tx_id)` constraint on sales and payments.
   - Retried submissions return the existing transaction record rather than charging twice.

---

## 4. AI Guardrails & Context Safety

1. **Tool-Calling Sandboxing**:
   - The AI Assistant has **zero direct SQL access**.
   - The AI interacts strictly via typed tool parameters (e.g., `DraftSaleInput`).
   - The backend validates all items, quantities, and prices against the tenant catalog before presenting the draft to the user.
2. **Two-Factor User Confirmation**:
   - The AI can *prepare* a transaction draft, but cannot *commit* financial mutations without explicit user interaction (e.g., clicking "Confirm Sale" or "Record Expense").
3. **Data Privacy**:
   - Only non-sensitive catalog items (product names, units, retail prices) are sent in the LLM prompt context to assist matching.
   - Complete customer ledgers, personal contact books, and overall balance sheets are never sent to external LLMs.

---

## 5. Defense in Depth & Web Security

- **SQL Injection**: Prevented universally by SQLAlchemy 2.0 parameterized queries and ORM mappings. Raw concatenated SQL is strictly prohibited.
- **Cross-Site Scripting (XSS)**: Handled via React JSX automatic string escaping and strict Content Security Policy (CSP).
- **CORS Configuration**: Restricts access to authorized frontend origins.
- **Rate Limiting**: Applied to `/auth/login`, `/auth/register`, and `/ai/` endpoints to protect against brute-force and resource exhaustion.
- **Environment & Secrets**: No secrets, tokens, or credentials committed to source control. Configuration loaded exclusively via `pydantic-settings` from environment variables.
