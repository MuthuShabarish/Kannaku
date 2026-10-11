import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_business, get_current_user
from app.models.business import Business
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.inventory import (
    StockAdjustmentCreate,
    StockMovementResponse,
    InventoryOverviewResponse
)
from app.services.inventory_service import (
    adjust_stock,
    list_stock_movements,
    get_inventory_overview
)

router = APIRouter(prefix="/api/v1/inventory", tags=["Inventory & Stock Management"])


@router.get("/overview", response_model=ApiResponse[InventoryOverviewResponse])
def get_overview(
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns aggregated stock metrics (total products, low stock, out of stock, valuation).
    """
    overview = get_inventory_overview(db, current_business.id)
    return ApiResponse(data=InventoryOverviewResponse(**overview))


@router.post("/adjustments", response_model=ApiResponse[StockMovementResponse], status_code=status.HTTP_201_CREATED)
def make_stock_adjustment(
    req: StockAdjustmentCreate,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes an atomic, concurrency-safe stock adjustment with mandatory audit reason.
    Prevents negative stock balances and logs full movement history.
    """
    movement = adjust_stock(
        db=db,
        business_id=current_business.id,
        user_id=current_user.id,
        req=req
    )
    return ApiResponse(
        data=StockMovementResponse(
            id=movement.id,
            business_id=movement.business_id,
            warehouse_id=movement.warehouse_id,
            product_id=movement.product_id,
            movement_type=movement.movement_type,
            quantity_delta=movement.quantity_delta,
            balance_after=movement.balance_after,
            unit_cost=movement.unit_cost,
            reason=movement.reason,
            created_by_user_id=movement.created_by_user_id,
            created_by_user_name=current_user.full_name,
            created_at=movement.created_at
        )
    )


@router.get("/movements", response_model=ApiResponse[List[StockMovementResponse]])
def get_movements(
    product_id: Optional[uuid.UUID] = Query(None, description="Filter movements by product ID"),
    movement_type: Optional[str] = Query(None, description="Filter by movement type (opening, adjustment_increase, etc.)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves chronological stock audit log for compliance and ledger traceability.
    """
    items, total_count = list_stock_movements(
        db=db,
        business_id=current_business.id,
        product_id=product_id,
        movement_type=movement_type,
        limit=limit,
        offset=offset
    )
    return ApiResponse(data=[StockMovementResponse(**item) for item in items])
