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

---

## ADR 010: Inventory Concurrency, Moving Average Costing & Strict Non-Negative Stock Policy
- **Status**: Accepted
- **Context**: In financial and inventory management, overselling and arbitrary stock overwrites cause inventory discrepancies, tax mismatches, and inaccurate gross profit calculations. Concurrent counter checkouts or simultaneous adjustments can create race conditions.
- **Decision**:
  - **No Direct Frontend Overwrites**: Stock balances (`InventoryBalance.current_stock`) can never be modified via generic product PUT/PATCH endpoints. All stock changes must go through dedicated, validated adjustment or transaction services.
  - **Traceable Stock Movements**: Every single stock balance change creates an immutable `StockMovement` row capturing business ID, warehouse ID, product ID, movement type, quantity delta, balance after, unit cost, responsible user, and mandatory audit reason.
  - **Pessimistic Concurrency Locking**: Stock adjustments acquire row-level locks via `with_for_update()` in PostgreSQL within database transactions to ensure race-free balance updates.
  - **Strict Non-Negative Policy**: Database check constraint `chk_current_stock_non_negative` (`current_stock >= 0`) and service-level validation strictly prevent stock from going below zero on adjustments or sales.
  - **Moving Average Cost (MAC)**: When stock is increased with an incoming unit cost, the weighted moving average unit cost is updated transactionally: `new_avg = ((current_stock * current_avg) + (delta * unit_cost)) / (current_stock + delta)`.
  - **Decimal Precision**: All stock quantities and monetary amounts use `NUMERIC(14, 4)` in PostgreSQL and Python `Decimal` to eliminate binary floating-point drift.
- **Consequence**: Guaranteed mathematical accuracy, complete auditability, and race condition immunity across all inventory operations.

---

## ADR 011: POS Atomic Checkout, COGS Snapshots, Idempotency & Customer Khata Accounting
- **Status**: Accepted
- **Context**: Point-of-Sale checkouts must guarantee zero overselling under concurrent checkouts, accurate moving-average cost of goods sold (COGS) snapshots, append-only historical invoice immutability, network-retry idempotency, and reconcile customer credit without double counting.
- **Decision**:
  - **Single PostgreSQL Transaction**: Checkout executes stock validation, pessimistic locking (`with_for_update()`), stock balance deduction, `StockMovement` creation, `SaleItem` snapshot creation, `Payment` records, and optional `CustomerLedgerEntry` updates in a single atomic database transaction. Any failure triggers a complete transaction rollback.
  - **Deterministic Deadlock Prevention**: Product IDs involved in a checkout cart are sorted before row-locking to guarantee identical lock ordering across concurrent checkout threads.
  - **Never Trust Frontend Calculations**: All subtotals, line discounts, overall discounts, total amount, and COGS are recalculated strictly on the backend using Python `Decimal` and Banker's rounding (`ROUND_HALF_EVEN`).
  - **Immutable Line-Item Snapshots**: `SaleItem` records permanently snapshot product name, SKU, unit, unit selling price, discount, and unit moving-average cost at the exact moment of sale. Future product edits or cost changes never modify past invoices.
  - **Idempotency Safeguard**: Invoices support a unique `(business_id, idempotency_key)` constraint. Repeated submissions return the previously completed invoice without double-deducting stock or double-charging payments.
  - **Customer Khata Ledger**:
    - Credit sales increase `Customer.current_balance` (positive = receivable).
    - Standalone payments against customer debt decrease `Customer.current_balance`.
    - Every balance change writes an immutable `CustomerLedgerEntry` with `entry_type`, `amount`, and `balance_after`.
    - Credit sales enforce configurable `credit_limit` checks.
- **Consequence**: Uncompromising financial integrity, reliable offline/retry idempotency, and audit-compliant Khata ledger tracking.

---

## ADR 012: Purchase Receiving, Landed Moving-Average Costing & Supplier AP Ledger
- **Status**: Accepted
- **Context**: Stage 5 introduces purchase invoices for goods received from suppliers. When goods are purchased, inventory quantities increase and unit costs must be integrated into the moving-average cost (MAC) without floating-point distortion. Additionally, supplier accounts-payable (AP) dues must be tracked atomically, and overall purchase discounts must be landed into inventory costs accurately.
- **Decision**:
  - **Landed Moving-Average Cost Calculation**:
    - For each item $i$: $\text{Line Net } L_i = (Q_i \times U_i) - D_{\text{line}, i}$.
    - Total line net subtotal $S = \sum L_i$.
    - Overall purchase discount $O$ is allocated proportionally: $O_i = (L_i / S) \times O$ (if $S > 0$, else 0).
    - Effective unit cost landed into inventory: $C_i = (L_i - O_i) / Q_i$.
    - New moving average cost: $\text{MAC}_{\text{new}} = \frac{(Q_{\text{old}} \times \text{MAC}_{\text{old}}) + (Q_i \times C_i)}{Q_{\text{old}} + Q_i}$. If $Q_{\text{old}} \le 0$, $\text{MAC}_{\text{new}} = C_i$.
  - **Deterministic Deadlock Prevention**:
    - Purchase transactions lock `InventoryBalance` rows via `with_for_update()` in ascending order of `product_id`.
  - **Supplier Accounts-Payable (AP) Ledger**:
    - `Supplier.current_balance` records positive balance as accounts payable (money owed by the business to the supplier).
    - Unpaid purchase amounts (`credit_amount`) increment `current_balance` and record an immutable `SupplierLedgerEntry` with `entry_type='credit_purchase'`.
    - Supplier payments decrement `current_balance` and record `SupplierLedgerEntry` with `entry_type='payment_made'`.
    - Oversettlement (`payment > current_balance`) is strictly rejected (`SETTLEMENT_EXCEEDS_BALANCE`). Payments on zero balance raise `NO_OUTSTANDING_BALANCE`. Payments to inactive suppliers raise `SUPPLIER_INACTIVE`.
  - **Historical Purchase Item Snapshot**:
    - `PurchaseItem` records snapshot `product_name`, `sku`, `unit`, `unit_cost`, `discount_amount`, `total_cost`, and `effective_unit_cost`.
  - **Idempotency & Reversibility**:
    - Purchases enforce a unique `(business_id, idempotency_key)` constraint.
    - Returns, cancellations with stock reversal, and statutory tax compliance are deferred out of scope.
- **Consequence**: Mathematical rigor, zero cost distortion across inventory items, strict tenant boundary enforcement, and audit-compliant accounts payable tracking.

---

## ADR 013: Operating Expenses & Transaction-Derived Cashbook Architecture
- **Status**: Accepted
- **Context**: Stage 6 introduces operating expenses and a unified cashbook. Operating expenses represent operational overhead (rent, utilities, wages, maintenance) that must not be confused with inventory purchases or sales cost of goods sold. Furthermore, businesses need an accurate, non-duplicative view of all money inflows and outflows across cash, UPI, cards, and bank transfers.
- **Decision**:
  - **Operating Expense Lifecycle & Audit Trail**:
    - `Expense` model captures `expense_number` (`EXP-YYYYMMDD-XXXX`), `category_id`, `amount`, `payment_method`, `payment_status` ('paid', 'unpaid', 'voided'), `payee`, `description`, `reference_number`, and `idempotency_key`.
    - Expenses cannot be deleted destructively if completed. Instead, a formal voiding mechanism (`POST /api/v1/expenses/{id}/void`) records `voided_at`, `voided_by_user_id`, and `void_reason`.
    - Voided expenses are permanently excluded from active expense totals and cashbook outflows.
  - **Expense Categories**:
    - Tenant-scoped `ExpenseCategory` with auto-seeding of sensible default operating categories (Rent, Electricity, Staff Wages, Transport, Repairs, Packaging, Internet, Supplies, Miscellaneous) on first access per business.
    - Custom categories can be created, updated, and deactivated. Deletion is forbidden if existing expenses reference the category.
  - **Transaction-Derived Cashbook Architecture (Zero Double-Counting)**:
    - Rather than maintaining a secondary duplicate ledger table that risks desynchronization and double-counting, the Cashbook service derives monetary movements directly from authoritative transactional records:
      1. **Sales Cash Inflows**: Derived from `Payment` records where `sale_id IS NOT NULL` and `payment_direction = 'inflow'` (captures immediate cash, UPI, card, and split payments). Unpaid credit sales do not enter the cashbook.
      2. **Customer Khata Collections**: Derived from `Payment` records where `customer_id IS NOT NULL` and `sale_id IS NULL` and `payment_direction = 'inflow'` (captures debt settlements when cash actually enters the business).
      3. **Purchase Cash Outflows**: Derived from `Payment` records where `purchase_id IS NOT NULL` and `payment_direction = 'outflow'` (captures immediate cash, UPI, card, and split payments on purchase receipt). Unpaid credit purchases do not enter the cashbook.
      4. **Supplier AP Settlements**: Derived from `Payment` records where `supplier_id IS NOT NULL` and `purchase_id IS NULL` and `payment_direction = 'outflow'` (captures debt settlements when cash leaves the business).
      5. **Operating Expenses**: Derived from `Expense` records where `payment_status = 'paid'` and `voided_at IS NULL`.
    - **Reconciliation & Integrity**:
      - Net Cash Movement is strictly calculated as $\text{Total Recorded Inflows} - \text{Total Recorded Outflows}$.
      - Clearly presented as *recorded transaction activity* without claiming external bank-reconciled balances or unverified cash drawers.
      - Full-range date and payment mode filtering supported across all transactions.
- **Consequence**: Guaranteed absence of double-counting, mathematical reconciliation against underlying primary records, full multi-tenant isolation, and complete audit transparency.



