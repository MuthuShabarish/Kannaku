# KANAKKU (கணக்கு) — Testing Strategy & Verification Plan

## 1. Testing Philosophy & Verification Pyramid

Kanakku handles real money, inventory assets, and customer credit. Every financial formula and concurrency path must have automated proof of correctness before merging.

```
       / \
      / E2E \       Critical Business Journeys (Cypress / Playwright)
     /-------\
    /  Integ  \     API + Database Transaction Tests (Pytest + Test DB)
   /-----------\
  /    Unit     \   Financial Math, Costing Formulas, Schema Validation
 /---------------\
```

---

## 2. Backend Automated Test Suite (Pytest)

### 2.1. Financial Math & Domain Unit Tests (`tests/unit/`)
- **Costing Formulas & Arithmetic**:
  - Test Moving Average Cost calculation with multiple incoming purchase lots at varying rates.
  - Test Gross Profit calculation: `Gross Revenue - COGS`. Verify zero division edge-cases.
  - Test Decimal precision: Ensure `0.1 + 0.2 == 0.3` exactness using `Decimal('0.1000')`.
  - Test Banker's Rounding (Round Half to Even) to 2 decimal places on fractional line items.
  - Test Configurable Cash Tender Rounding (exact vs nearest ₹1 integer).
- **Stock Movement Integrity**:
  - Verify that opening stock + purchases - sales + returns = ending balance.
  - Verify rejection of negative stock when business setting `allow_negative_stock == False`.

### 2.2. Authentication & Security Unit/Integration Tests (`tests/security/`)
- **Credential Storage**: Assert that plaintext passwords or PINs are NEVER stored in the database or returned in any API response.
- **Argon2id Hashing**: Verify password verification with varying salt lengths and cost parameters.
- **Brute-Force & Lockout**: Simulate 5 rapid incorrect PIN submissions; assert account enters 15-minute temporary lockout with HTTP 429 / 403 response.
- **Session & Refresh Token Rotation**: Test that issuing a new access token rotates the refresh token. Test that presenting an old/revoked refresh token immediately invalidates all active sessions for that user family.
- **Tenant Scope Enforcement**: Assert that attempting to access `/api/v1/sales` or `/api/v1/catalog` belonging to Business A with a valid token for Business B returns `404 Not Found` or `403 Forbidden` with zero data leakage.

### 2.3. Mandatory PostgreSQL Integration Tests (`tests/integration_postgres/`)
*PostgreSQL 16+ is the canonical target; tests in this suite run against a real PostgreSQL instance to validate behaviors SQLite cannot replicate:*
- **Concurrent Row-Level Locking (`FOR UPDATE`)**:
  - Spawn 10 simultaneous worker threads attempting to purchase the last 3 units of an item.
  - Assert that PostgreSQL row-locking prevents race conditions, exactly 3 units are sold, and remaining 7 threads receive clean `INSUFFICIENT_STOCK` errors.
- **Database Constraints & Triggers**:
  - Verify PostgreSQL check constraint `CHECK (current_stock >= 0)` rejects negative balances at the database engine level.
  - Verify PostgreSQL foreign key `ON DELETE RESTRICT` blocks deleting products that have linked historical sale items.
- **Transactional Rollbacks & ACID Guarantees**:
  - Simulate network or validation failure mid-transaction (e.g., payment fails after stock decrement).
  - Assert complete database rollback with zero orphaned inventory or sales records.
- **Multi-Tenant Transaction Isolation**:
  - Verify that concurrent transactions from two different businesses execute in complete isolation without locking each other's tables or leaking state.

---

## 3. Frontend Component & Experience Testing

### 3.1. Reusable Component Verification
- **Keypad Component**:
  - Verify rapid number entry, decimal point handling, backspace, and quick shortcut additions.
- **Adaptive UI Switcher**:
  - Verify rendering of Simple jumbo touch pad when tier is `simple`.
  - Verify rendering of multi-item grid and advanced filters when tier is `growth` or `enterprise`.
- **I18n Localization Verification**:
  - Verify that language switch updates all visible labels across Tamil, Tanglish, and English without layout clipping or Unicode broken glyphs.

---

## 4. End-to-End Critical Journey Tests

### Journey 1: Adaptive Onboarding
1. Unregistered user signs up with Phone and Name.
2. Answers 5-step guided questionnaire: 1 person, retail vegetables, cash only, Tamil preferred.
3. System deduces `Kanakku Simple` tier and configures Tamil language.
4. Dashboard launches showing 5 core daily metrics.

### Journey 2: 5-Second Quick Sale (Kanakku Simple)
1. Shopkeeper taps "Apple", enters "120", taps "Cash".
2. Transaction completes in under 2 clicks.
3. Sale is recorded, inventory stock is decremented, cash drawer expected balance increments by ₹120.
4. Daily summary updates instantly.

### Journey 3: Customer Credit (Udhar) & Settlement
1. Sale of ₹500 made to Customer "Murugan" with ₹200 paid in cash and ₹300 on credit.
2. Verify:
   - Cash drawer increments by ₹200 (not ₹500).
   - Murugan's ledger balance shows ₹300 receivable.
   - Revenue shows ₹500.
3. Next day, Murugan pays ₹300 via UPI.
4. Verify:
   - Murugan's balance returns to ₹0.
   - Bank/UPI balance increments by ₹300.
   - Sales revenue for the new day does NOT increase (preventing double revenue counting).

### Journey 4: Safe AI Voice Billing
1. User provides natural language prompt in Tamil: "ரெண்டு மூட்டை அரிசி 1100 ரூபாய் கடன் குமார்".
2. AI parses: Product="அரிசி", Qty=2, Price=1100, Payment="Credit", Customer="குமார்".
3. System displays interactive confirmation card.
4. User clicks "Confirm"; transaction commits safely to database.
