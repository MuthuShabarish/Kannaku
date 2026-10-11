# KANAKKU (கணக்கு) — Database Architecture & Integrity Specification

## 1. Core Database Philosophy

Financial software lives or dies by the integrity of its data layer. Kanakku enforces strict relational database guarantees:
- **Canonical Database Engine**: **PostgreSQL 16+** is the primary, canonical database for both development and production. All schema features, constraints, indexes, transaction isolation levels, and concurrency models are designed natively for PostgreSQL.
- **SQLite Auxiliary Caveat**: SQLite may be utilized *only* as a temporary, lightweight fallback for offline unit tests in environments lacking Docker/Postgres. **SQLite must NOT be treated as behaviorally identical to PostgreSQL**. Critical differences documented and accounted for:
  - SQLite lacks row-level locking (`SELECT ... FOR UPDATE`); it uses coarse database-level locking.
  - SQLite does not support native `NUMERIC(14, 4)` fixed-point arithmetic (it converts to REAL floating-point or TEXT unless strictly cast).
  - SQLite does not enforce PostgreSQL-style `ALTER TABLE` constraints or transactional DDL in the same manner.
  - SQLite lacks PostgreSQL's native `TIMESTAMPTZ` and `JSONB` binary indexing.
- **Mandatory PostgreSQL Integration Tests**: The test pipeline must include a dedicated PostgreSQL test suite validating:
  - Multi-threaded concurrent inventory deductions (row-level locking).
  - Strict check constraints (e.g., `current_stock >= 0`).
  - Foreign key cascading and deletion restrictions (`ON DELETE RESTRICT`).
  - Strict tenant boundary isolation across transactions.
- **Monetary Precision & Currency Rules**:
  - Default Currency: **Indian Rupee (₹ / INR)**.
  - Every business specifies a configurable `currency_code` (e.g., INR, USD, EUR, AED) and `currency_symbol`.
  - All financial fields use `NUMERIC(14, 4)` in PostgreSQL to prevent rounding drift in unit costs, taxes, and discounts.
  - Explicit rounding rules:
    - Line item subtotals and taxes: Banker's Rounding (Round Half to Even) to 2 decimal places.
    - Cash tender display: Configurable rounding (Exact 2 decimals, or Round to nearest integer ₹1 for cash counter efficiency in micro-retail).
- **Append-Only Corrections**: Completed invoices, payments, and stock movements are **never mutated or deleted silently**. Corrections must be recorded via **credit notes, debit notes, returns, or reversal entries**.
- **Atomic Concurrency Control**: Stock level changes and cash drawer balances use database transactions with pessimistic row-locking (`SELECT ... FOR UPDATE` in PostgreSQL) or atomic decrement expressions (`WHERE current_stock >= :qty`) to eliminate overselling and race conditions.

---

## 2. Inventory Costing Methodology

Kanakku uses the **Moving Average Cost (MAC)** method by default:

$$\text{New Average Cost} = \frac{(\text{Current Qty} \times \text{Current Avg Cost}) + (\text{Incoming Qty} \times \text{Purchase Unit Cost})}{\text{Current Qty} + \text{Incoming Qty}}$$

### Costing Guarantees:
1. **Goods Receipt**: When a purchase invoice or GRN is posted, the unit cost updates the weighted average for that product/variant in that warehouse.
2. **Sales COGS**: When an item is sold, the Cost of Goods Sold (COGS) is recorded at the item's instantaneous average cost at that moment:
   $$\text{COGS} = \text{Sold Quantity} \times \text{Current Average Cost}$$
3. **Gross Profit**:
   $$\text{Gross Profit} = \text{Net Sale Amount} - \text{COGS}$$
4. **Historical Immutability**: Subsequent purchases at higher or lower prices do not retroactively alter the COGS of historical sales.

---

## 3. Entity Specification & Tables

### 3.1. Tenant & Organization Structure
- `businesses`:
  - `id`: UUID (Primary Key)
  - `name`: VARCHAR(255) NOT NULL
  - `category`: VARCHAR(100) (e.g., Grocery, Textile, Manufacturing, Service)
  - `tier`: VARCHAR(20) DEFAULT 'simple' ('simple', 'growth', 'enterprise')
  - `currency_code`: VARCHAR(3) DEFAULT 'INR'
  - `currency_symbol`: VARCHAR(5) DEFAULT '₹'
  - `default_language`: VARCHAR(10) DEFAULT 'ta' ('ta', 'tanglish', 'en', 'hi', etc.)
  - `settings`: JSONB (tax configs, print preferences, voice settings, module flags)
  - `created_at`, `updated_at`: TIMESTAMPTZ NOT NULL
- `branches`:
  - `id`: UUID (Primary Key)
  - `business_id`: UUID (FK -> businesses.id ON DELETE CASCADE)
  - `name`: VARCHAR(255) NOT NULL
  - `code`: VARCHAR(50) (e.g., BR-01)
  - `address`: TEXT, `phone`: VARCHAR(20)
  - `is_main`: BOOLEAN DEFAULT FALSE
  - `is_active`: BOOLEAN DEFAULT TRUE
  - `created_at`: TIMESTAMPTZ NOT NULL
- `warehouses`:
  - `id`: UUID (Primary Key)
  - `business_id`: UUID (FK -> businesses.id ON DELETE CASCADE)
  - `branch_id`: UUID (FK -> branches.id ON DELETE CASCADE)
  - `name`: VARCHAR(255) NOT NULL (e.g., "Main Godown", "Front Counter")
  - `is_default`: BOOLEAN DEFAULT FALSE

### 3.2. Access Control & Identity
- `users`:
  - `id`: UUID (Primary Key)
  - `business_id`: UUID (FK -> businesses.id ON DELETE CASCADE)
  - `email`: VARCHAR(255) UNIQUE (optional for simple shopkeeper)
  - `phone`: VARCHAR(20) NOT NULL
  - `full_name`: VARCHAR(255) NOT NULL
  - `password_hash`: VARCHAR(255) NOT NULL
  - `role`: VARCHAR(50) NOT NULL ('owner', 'manager', 'cashier', 'biller', 'auditor')
  - `preferred_language`: VARCHAR(10) DEFAULT 'ta'
  - `is_active`: BOOLEAN DEFAULT TRUE
  - `created_at`, `updated_at`: TIMESTAMPTZ NOT NULL
- `audit_logs`:
  - `id`: UUID (Primary Key)
  - `business_id`: UUID (FK -> businesses.id)
  - `user_id`: UUID (FK -> users.id NULLABLE)
  - `entity_type`: VARCHAR(100) NOT NULL ('sale', 'payment', 'stock_adjustment', etc.)
  - `entity_id`: UUID NOT NULL
  - `action`: VARCHAR(50) NOT NULL ('create', 'cancel', 'reversal', 'credit_writeoff')
  - `old_state`: JSONB, `new_state`: JSONB
  - `reason`: TEXT
  - `ip_address`: VARCHAR(45)
  - `created_at`: TIMESTAMPTZ NOT NULL

### 3.3. Catalog & Inventory
- `categories`:
  - `id`: UUID (PK), `business_id`: UUID (FK)
  - `name`: VARCHAR(255) NOT NULL, `tamil_name`: VARCHAR(255)
  - `display_order`: INTEGER DEFAULT 0
- `units`:
  - `id`: UUID (PK), `business_id`: UUID (FK)
  - `code`: VARCHAR(20) NOT NULL (kg, g, l, ml, piece, packet, box, meter)
  - `name`: VARCHAR(100) NOT NULL
  - `allow_decimal`: BOOLEAN DEFAULT FALSE (e.g., TRUE for kg/meter, FALSE for piece)
- `products`:
  - `id`: UUID (PK), `business_id`: UUID (FK)
  - `category_id`: UUID (FK -> categories.id NULLABLE)
  - `name`: VARCHAR(255) NOT NULL, `tamil_name`: VARCHAR(255)
  - `barcode`: VARCHAR(100) NULLABLE (indexed per business)
  - `sku`: VARCHAR(100) NULLABLE
  - `unit_id`: UUID (FK -> units.id)
  - `default_sales_price`: NUMERIC(14, 4) NOT NULL
  - `default_purchase_price`: NUMERIC(14, 4) DEFAULT 0
  - `average_cost`: NUMERIC(14, 4) DEFAULT 0
  - `min_stock_alert`: NUMERIC(14, 4) DEFAULT 0
  - `is_manufactured`: BOOLEAN DEFAULT FALSE
  - `is_active`: BOOLEAN DEFAULT TRUE
- `inventory_balances`:
  - `id`: UUID (PK), `business_id`: UUID (FK)
  - `warehouse_id`: UUID (FK -> warehouses.id)
  - `product_id`: UUID (FK -> products.id)
  - `current_stock`: NUMERIC(14, 4) NOT NULL DEFAULT 0
  - `reserved_stock`: NUMERIC(14, 4) NOT NULL DEFAULT 0
  - `average_cost`: NUMERIC(14, 4) NOT NULL DEFAULT 0
  - *Constraint*: `UNIQUE(warehouse_id, product_id)`
  - *Check Constraint*: `current_stock >= 0` (in strict mode)
- `stock_movements`:
  - `id`: UUID (PK), `business_id`: UUID (FK)
  - `warehouse_id`: UUID (FK -> warehouses.id)
  - `product_id`: UUID (FK -> products.id)
  - `movement_type`: VARCHAR(50) NOT NULL ('opening', 'sale', 'purchase', 'return', 'adjustment', 'transfer_in', 'transfer_out', 'production_consume', 'production_yield')
  - `reference_id`: UUID NULLABLE (FK to sale_id, purchase_id, etc.)
  - `quantity_delta`: NUMERIC(14, 4) NOT NULL (positive for in, negative for out)
  - `balance_after`: NUMERIC(14, 4) NOT NULL
  - `unit_cost`: NUMERIC(14, 4) NOT NULL
  - `created_at`: TIMESTAMPTZ NOT NULL

### 3.4. Commercial Parties (Customers & Suppliers)
- `parties`:
  - `id`: UUID (PK), `business_id`: UUID (FK)
  - `party_type`: VARCHAR(20) NOT NULL ('customer', 'supplier', 'both')
  - `name`: VARCHAR(255) NOT NULL
  - `phone`: VARCHAR(20) NOT NULL
  - `address`: TEXT
  - `credit_limit`: NUMERIC(14, 4) DEFAULT 0
  - `current_balance`: NUMERIC(14, 4) DEFAULT 0 (Positive = Receivable/Owed to shop; Negative = Payable)
  - `is_active`: BOOLEAN DEFAULT TRUE

### 3.5. Sales & Billing
- `sales`:
  - `id`: UUID (PK), `business_id`: UUID (FK)
  - `branch_id`: UUID (FK -> branches.id)
  - `warehouse_id`: UUID (FK -> warehouses.id)
  - `invoice_number`: VARCHAR(100) NOT NULL
  - `client_tx_id`: VARCHAR(100) UNIQUE NULLABLE (Idempotency key for offline sync)
  - `party_id`: UUID (FK -> parties.id NULLABLE - Walk-in customer allowed)
  - `status`: VARCHAR(30) NOT NULL ('draft', 'completed', 'reversed', 'cancelled')
  - `subtotal_amount`: NUMERIC(14, 4) NOT NULL
  - `discount_amount`: NUMERIC(14, 4) NOT NULL DEFAULT 0
  - `tax_amount`: NUMERIC(14, 4) NOT NULL DEFAULT 0
  - `total_amount`: NUMERIC(14, 4) NOT NULL
  - `paid_amount`: NUMERIC(14, 4) NOT NULL DEFAULT 0
  - `credit_amount`: NUMERIC(14, 4) NOT NULL DEFAULT 0 (total - paid)
  - `cogs_total`: NUMERIC(14, 4) NOT NULL DEFAULT 0 (Sum of line COGS)
  - `created_by_user_id`: UUID (FK -> users.id)
  - `created_at`: TIMESTAMPTZ NOT NULL
- `sale_items`:
  - `id`: UUID (PK), `sale_id`: UUID (FK -> sales.id ON DELETE RESTRICT)
  - `product_id`: UUID (FK -> products.id)
  - `quantity`: NUMERIC(14, 4) NOT NULL
  - `unit_price`: NUMERIC(14, 4) NOT NULL
  - `unit_cost`: NUMERIC(14, 4) NOT NULL (Average cost at moment of sale)
  - `discount_amount`: NUMERIC(14, 4) DEFAULT 0
  - `tax_rate`: NUMERIC(6, 4) DEFAULT 0
  - `total_price`: NUMERIC(14, 4) NOT NULL

### 3.6. Purchases & Suppliers
- `purchases`:
  - `id`: UUID (PK), `business_id`: UUID (FK)
  - `supplier_id`: UUID (FK -> parties.id)
  - `warehouse_id`: UUID (FK -> warehouses.id)
  - `invoice_number`: VARCHAR(100) NOT NULL
  - `total_amount`: NUMERIC(14, 4) NOT NULL
  - `paid_amount`: NUMERIC(14, 4) NOT NULL DEFAULT 0
  - `status`: VARCHAR(30) NOT NULL ('received', 'partial', 'cancelled')
  - `created_at`: TIMESTAMPTZ NOT NULL
- `purchase_items`:
  - `id`: UUID (PK), `purchase_id`: UUID (FK -> purchases.id)
  - `product_id`: UUID (FK -> products.id)
  - `quantity`: NUMERIC(14, 4) NOT NULL
  - `unit_purchase_cost`: NUMERIC(14, 4) NOT NULL
  - `total_cost`: NUMERIC(14, 4) NOT NULL

### 3.7. Payments, Expenses & Cash Drawer
- `payments`:
  - `id`: UUID (PK), `business_id`: UUID (FK)
  - `party_id`: UUID (FK -> parties.id NULLABLE)
  - `reference_sale_id`: UUID (FK -> sales.id NULLABLE)
  - `reference_purchase_id`: UUID (FK -> purchases.id NULLABLE)
  - `payment_direction`: VARCHAR(20) NOT NULL ('inflow' / 'outflow')
  - `payment_mode`: VARCHAR(30) NOT NULL ('cash', 'upi', 'card', 'bank_transfer')
  - `amount`: NUMERIC(14, 4) NOT NULL
  - `payment_date`: TIMESTAMPTZ NOT NULL
- `expenses`:
  - `id`: UUID (PK), `business_id`: UUID (FK)
  - `category`: VARCHAR(100) NOT NULL (e.g., Rent, Electricity, Tea/Snacks, Transport, Wages)
  - `amount`: NUMERIC(14, 4) NOT NULL
  - `payment_mode`: VARCHAR(30) NOT NULL ('cash', 'upi', 'bank')
  - `notes`: TEXT
  - `created_by_user_id`: UUID (FK -> users.id)
  - `created_at`: TIMESTAMPTZ NOT NULL
- `cash_sessions` (Daily Closing / Register Drawer):
  - `id`: UUID (PK), `business_id`: UUID (FK), `branch_id`: UUID (FK)
  - `user_id`: UUID (FK -> users.id)
  - `opening_cash`: NUMERIC(14, 4) NOT NULL
  - `expected_cash`: NUMERIC(14, 4) NOT NULL (Calculated from Cash Sales + Debt Inflow - Expenses)
  - `actual_cash_counted`: NUMERIC(14, 4) NULLABLE
  - `cash_difference`: NUMERIC(14, 4) NULLABLE (Actual - Expected)
  - `status`: VARCHAR(20) NOT NULL ('open', 'closed')
  - `opened_at`: TIMESTAMPTZ NOT NULL, `closed_at`: TIMESTAMPTZ NULLABLE

---

## 4. Indexing Strategy

1. **Tenant Filtering**: Every table has index on `business_id`.
2. **Sales Search & Reports**: `(business_id, created_at)`, `(business_id, invoice_number)`, `(business_id, party_id)`.
3. **Inventory Fast Lookup**: `(business_id, barcode)`, `(warehouse_id, product_id)`.
4. **Idempotency Protection**: `(business_id, client_tx_id)` UNIQUE constraint.
