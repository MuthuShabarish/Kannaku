# KANAKKU (கணக்கு) — REST API Specification

## 1. General API Conventions

- **Base Path**: `/api/v1`
- **Protocol**: HTTPS / JSON
- **Authentication**: JWT Bearer token via `Authorization: Bearer <jwt_token>` header.
- **Tenant Scope**: Tenant is resolved from token claims or optional `X-Business-ID: <uuid>` header for multi-business owners.
- **Standard Error Response**:
```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "Only 3.5 kg of 'Red Apple' remaining in warehouse Main Godown.",
    "field": "items[0].quantity",
    "details": {
      "product_id": "8f9d0c2e-4b21-4f11-92ab-112233445566",
      "available_stock": 3.5,
      "requested_quantity": 5.0
    }
  }
}
```

---

## 2. API Modules & Endpoints

### 2.1. Authentication & Users (`/api/v1/auth`)
| Method | Endpoint | Description | Roles |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Register new business owner + business account | Public |
| `POST` | `/auth/login` | Login with phone/email and password | Public |
| `GET` | `/auth/me` | Fetch active user profile, business list, and roles | Authenticated |
| `POST` | `/auth/refresh` | Refresh JWT access token | Authenticated |
| `POST` | `/auth/switch-business` | Switch active tenant context | Owner / Multi-tenant |

### 2.2. Adaptive Onboarding (`/api/v1/onboarding`)
| Method | Endpoint | Description | Roles |
| :--- | :--- | :--- | :--- |
| `GET` | `/onboarding/status` | Check onboarding progress & current step | Authenticated |
| `POST` | `/onboarding/submit-step` | Submit answer for single step (1-question-at-a-time) | Owner |
| `POST` | `/onboarding/recommend-tier` | Evaluate rules to recommend Simple/Growth/Enterprise | Owner |
| `POST` | `/onboarding/finalize` | Commit initial configuration and enable modules | Owner |
| `PUT` | `/business/settings` | Update preferences (language, currency, voice, modules) | Owner |

### 2.3. Catalog & Units (`/api/v1/catalog`)
| Method | Endpoint | Description | Roles |
| :--- | :--- | :--- | :--- |
| `GET` | `/catalog/categories` | List product categories | Cashier, Manager, Owner |
| `POST` | `/catalog/categories` | Create new category | Manager, Owner |
| `GET` | `/catalog/units` | List units of measurement (kg, piece, etc.) | All |
| `GET` | `/catalog/products` | Search/list products with stock & prices | All |
| `POST` | `/catalog/products` | Create product with default prices and unit | Manager, Owner |
| `PUT` | `/catalog/products/{id}` | Update product details | Manager, Owner |
| `GET` | `/catalog/products/quick-list`| Fast list of top items for Simple Touch Pad | All |

### 2.4. Inventory Management (`/api/v1/inventory`)
| Method | Endpoint | Description | Roles |
| :--- | :--- | :--- | :--- |
| `GET` | `/inventory/balances` | Warehouse-wise current stock levels | All |
| `POST` | `/inventory/adjustments` | Record manual adjustment (damage, recount, theft) | Manager, Owner |
| `POST` | `/inventory/transfers` | Transfer stock between branches/warehouses | Manager, Owner |
| `GET` | `/inventory/movements` | Immutable audit log of stock movements | Manager, Owner |
| `GET` | `/inventory/low-stock` | Items below minimum reorder alert level | All |

### 2.5. Parties & Ledgers (`/api/v1/parties`)
| Method | Endpoint | Description | Roles |
| :--- | :--- | :--- | :--- |
| `GET` | `/parties` | List customers or suppliers with current balances | All |
| `POST` | `/parties` | Create new customer or supplier | All |
| `GET` | `/parties/{id}/ledger` | View statement of credit transactions & payments | All |
| `POST` | `/parties/{id}/payments` | Record credit collection (Udhar repayment) / payment | All |

### 2.6. Sales & POS Billing (`/api/v1/sales`)
| Method | Endpoint | Description | Roles |
| :--- | :--- | :--- | :--- |
| `POST` | `/sales/quick-bill` | 1-touch quick sale for Kanakku Simple | Cashier, Owner |
| `POST` | `/sales` | Detailed multi-item invoice with tax/discounts | Cashier, Manager, Owner |
| `GET` | `/sales` | Paginated sales invoices | All |
| `GET` | `/sales/{id}` | Invoice details with item lines & payments | All |
| `POST` | `/sales/{id}/reverse` | Full or partial reversal with credit note | Manager, Owner |

### 2.7. Purchases & Suppliers (`/api/v1/purchases`)
| Method | Endpoint | Description | Roles |
| :--- | :--- | :--- | :--- |
| `POST` | `/purchases` | Record goods receipt & update moving average costs | Manager, Owner |
| `GET` | `/purchases` | List purchase records | Manager, Owner |
| `GET` | `/purchases/{id}` | Detailed purchase invoice | Manager, Owner |

### 2.8. Operational Expenses (`/api/v1/expenses`)
| Method | Endpoint | Description | Roles |
| :--- | :--- | :--- | :--- |
| `POST` | `/expenses` | Log store expense (Rent, Tea, Electricity, Fuel) | Cashier, Owner |
| `GET` | `/expenses` | List daily / monthly expenses | Manager, Owner |
| `GET` | `/expenses/categories` | Predefined & custom expense categories | All |

### 2.9. Daily Closing & Cash Drawer (`/api/v1/closing`)
| Method | Endpoint | Description | Roles |
| :--- | :--- | :--- | :--- |
| `POST` | `/closing/open-session` | Open daily cash session with starting cash | Cashier, Owner |
| `GET` | `/closing/current-session` | Current session running totals (sales, expenses) | Cashier, Owner |
| `POST` | `/closing/close-session` | Count cash, compute over/short variance & lock day | Cashier, Owner |
| `GET` | `/closing/summary/today` | Quick 5-metric answers for Kanakku Simple | Cashier, Owner |

### 2.10. Financial & Valuation Reports (`/api/v1/reports`)
| Method | Endpoint | Description | Roles |
| :--- | :--- | :--- | :--- |
| `GET` | `/reports/profit-loss` | True P&L (Gross Revenue - COGS - Expenses) | Manager, Owner |
| `GET` | `/reports/stock-valuation` | Stock inventory valuation (Qty * Moving Avg Cost) | Manager, Owner |
| `GET` | `/reports/receivables-payables`| Outstanding customer credit & supplier dues | Manager, Owner |
| `GET` | `/reports/export` | Export CSV / PDF format | Manager, Owner |

### 2.11. AI Assistant Engine (`/api/v1/ai`)
| Method | Endpoint | Description | Roles |
| :--- | :--- | :--- | :--- |
| `POST` | `/ai/parse-intent` | Parse voice/text prompt into structured action draft | All |
| `POST` | `/ai/ask-query` | Natural language business Q&A from authorized data | All |
| `POST` | `/ai/execute-action` | Confirmed tool-call execution through business APIs | All |

### 2.12. Offline Queue & Sync (`/api/v1/sync`)
| Method | Endpoint | Description | Roles |
| :--- | :--- | :--- | :--- |
| `POST` | `/sync/transactions` | Batch upload queued offline transactions with UUID | Cashier, Owner |
| `GET` | `/sync/catalog-snapshot` | Download lightweight offline catalog for local cache| All |
