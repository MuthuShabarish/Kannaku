import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict


class CashbookTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str  # Composite or source ID string
    source_type: str  # 'sale_payment', 'customer_settlement', 'purchase_payment', 'supplier_settlement', 'operating_expense'
    source_id: uuid.UUID
    transaction_date: datetime
    direction: str  # 'inflow' or 'outflow'
    amount: Decimal
    payment_mode: str  # 'cash', 'upi', 'card', 'bank_transfer'
    category: str  # e.g., "Sale Revenue", "Customer Khata Collection", "Inventory Purchase", "Supplier AP Settlement", "Rent"
    reference: Optional[str] = None  # Invoice #, Purchase #, Expense #, or receipt #
    party_name: Optional[str] = None  # Customer name, Supplier name, Payee
    description: Optional[str] = None


class CashbookSummaryResponse(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    total_inflows: Decimal
    total_outflows: Decimal
    net_cash_movement: Decimal  # total_inflows - total_outflows
    inflows_by_mode: Dict[str, Decimal]
    outflows_by_mode: Dict[str, Decimal]
    transaction_count: int
    disclosure: str = "Recorded transaction activity derived from sales, Khata collections, purchases, supplier settlements, and operating expenses."
