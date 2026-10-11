import uuid
from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc, asc
from fastapi import HTTPException, status

from app.models.business import Business, Branch, Warehouse
from app.models.user import User
from app.models.inventory import Category, Product, InventoryBalance, StockMovement
from app.schemas.inventory import (
    CategoryCreate,
    CategoryUpdate,
    ProductCreate,
    ProductUpdate,
    StockAdjustmentCreate
)


def get_default_warehouse(db: Session, business_id: uuid.UUID) -> Warehouse:
    """Finds or ensures a default warehouse for the given business."""
    warehouse = (
        db.query(Warehouse)
        .filter(Warehouse.business_id == business_id, Warehouse.is_default == True, Warehouse.is_active == True)
        .first()
    )
    if not warehouse:
        warehouse = (
            db.query(Warehouse)
            .filter(Warehouse.business_id == business_id, Warehouse.is_active == True)
            .first()
        )
    if not warehouse:
        # Create a fallback branch and warehouse if none exists
        branch = (
            db.query(Branch)
            .filter(Branch.business_id == business_id, Branch.is_active == True)
            .first()
        )
        if not branch:
            branch = Branch(
                business_id=business_id,
                name="Main Branch",
                code="BR-01",
                is_main=True,
                is_active=True
            )
            db.add(branch)
            db.flush()

        warehouse = Warehouse(
            business_id=business_id,
            branch_id=branch.id,
            name="Main Counter",
            is_default=True,
            is_active=True
        )
        db.add(warehouse)
        db.flush()

    return warehouse


# ==========================================
# CATEGORY SERVICES
# ==========================================

def create_category(db: Session, business_id: uuid.UUID, req: CategoryCreate) -> Category:
    clean_name = req.name.strip()
    existing = (
        db.query(Category)
        .filter(Category.business_id == business_id, func.lower(Category.name) == clean_name.lower())
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CATEGORY_ALREADY_EXISTS",
                "message": f"Category '{clean_name}' already exists in your business.",
                "field": "name"
            }
        )

    category = Category(
        business_id=business_id,
        name=clean_name,
        tamil_name=req.tamil_name.strip() if req.tamil_name else None,
        display_order=req.display_order,
        is_active=True
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def list_categories(db: Session, business_id: uuid.UUID) -> List[Tuple[Category, int]]:
    """Returns categories for business with their product count."""
    results = (
        db.query(
            Category,
            func.count(Product.id).label("product_count")
        )
        .outerjoin(Product, and_(Product.category_id == Category.id, Product.is_active == True))
        .filter(Category.business_id == business_id)
        .group_by(Category.id)
        .order_by(Category.display_order.asc(), Category.name.asc())
        .all()
    )
    return results


def update_category(db: Session, business_id: uuid.UUID, category_id: uuid.UUID, req: CategoryUpdate) -> Category:
    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.business_id == business_id)
        .first()
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CATEGORY_NOT_FOUND", "message": "Category not found."}
        )

    if req.name is not None:
        clean_name = req.name.strip()
        conflict = (
            db.query(Category)
            .filter(
                Category.business_id == business_id,
                Category.id != category_id,
                func.lower(Category.name) == clean_name.lower()
            )
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "CATEGORY_ALREADY_EXISTS",
                    "message": f"Category '{clean_name}' already exists.",
                    "field": "name"
                }
            )
        category.name = clean_name

    if req.tamil_name is not None:
        category.tamil_name = req.tamil_name.strip() if req.tamil_name else None
    if req.display_order is not None:
        category.display_order = req.display_order
    if req.is_active is not None:
        category.is_active = req.is_active

    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, business_id: uuid.UUID, category_id: uuid.UUID) -> None:
    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.business_id == business_id)
        .first()
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CATEGORY_NOT_FOUND", "message": "Category not found."}
        )

    # Reassign products in this category to unassigned (SET NULL)
    db.query(Product).filter(Product.category_id == category_id).update({"category_id": None})
    db.delete(category)
    db.commit()


# ==========================================
# PRODUCT SERVICES
# ==========================================

def create_product(
    db: Session,
    business_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    req: ProductCreate
) -> Tuple[Product, Decimal]:
    # 1. Check SKU uniqueness if provided
    clean_sku = req.sku.strip() if req.sku else None
    if clean_sku:
        existing_sku = (
            db.query(Product)
            .filter(Product.business_id == business_id, func.lower(Product.sku) == clean_sku.lower())
            .first()
        )
        if existing_sku:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "SKU_ALREADY_EXISTS",
                    "message": f"Product with SKU '{clean_sku}' already exists in your business.",
                    "field": "sku"
                }
            )

    # 2. Validate category belongs to business if provided
    if req.category_id:
        cat = (
            db.query(Category)
            .filter(Category.id == req.category_id, Category.business_id == business_id)
            .first()
        )
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "CATEGORY_NOT_FOUND", "message": "Specified category does not exist."}
            )

    # 3. Create Product entity
    product = Product(
        business_id=business_id,
        category_id=req.category_id,
        name=req.name.strip(),
        tamil_name=req.tamil_name.strip() if req.tamil_name else None,
        description=req.description.strip() if req.description else None,
        sku=clean_sku,
        unit=req.unit.strip().lower() if req.unit else "piece",
        purchase_cost=req.purchase_cost,
        selling_price=req.selling_price,
        low_stock_threshold=req.low_stock_threshold,
        is_active=req.is_active
    )
    db.add(product)
    db.flush()

    # 4. Resolve default warehouse and create initial InventoryBalance
    warehouse = get_default_warehouse(db, business_id)
    opening_qty = req.opening_stock if req.opening_stock is not None else Decimal("0.0000")
    cost_per_unit = req.opening_stock_cost if req.opening_stock_cost is not None else req.purchase_cost

    balance = InventoryBalance(
        business_id=business_id,
        warehouse_id=warehouse.id,
        product_id=product.id,
        current_stock=opening_qty,
        reserved_stock=Decimal("0.0000"),
        average_cost=cost_per_unit
    )
    db.add(balance)

    # 5. If opening stock > 0, record initial stock movement
    if opening_qty > 0:
        movement = StockMovement(
            business_id=business_id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            movement_type="opening",
            quantity_delta=opening_qty,
            balance_after=opening_qty,
            unit_cost=cost_per_unit,
            reason="Opening stock balance",
            created_by_user_id=user_id
        )
        db.add(movement)

    db.commit()
    db.refresh(product)
    return product, opening_qty


def update_product(
    db: Session,
    business_id: uuid.UUID,
    product_id: uuid.UUID,
    req: ProductUpdate
) -> Product:
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.business_id == business_id)
        .first()
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PRODUCT_NOT_FOUND", "message": "Product not found."}
        )

    if req.name is not None:
        product.name = req.name.strip()

    if req.tamil_name is not None:
        product.tamil_name = req.tamil_name.strip() if req.tamil_name else None

    if req.description is not None:
        product.description = req.description.strip() if req.description else None

    if req.sku is not None:
        clean_sku = req.sku.strip() if req.sku else None
        if clean_sku:
            existing_sku = (
                db.query(Product)
                .filter(
                    Product.business_id == business_id,
                    Product.id != product_id,
                    func.lower(Product.sku) == clean_sku.lower()
                )
                .first()
            )
            if existing_sku:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "SKU_ALREADY_EXISTS",
                        "message": f"Product with SKU '{clean_sku}' already exists in your business.",
                        "field": "sku"
                    }
                )
        product.sku = clean_sku

    if req.category_id is not None:
        if req.category_id:
            cat = (
                db.query(Category)
                .filter(Category.id == req.category_id, Category.business_id == business_id)
                .first()
            )
            if not cat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "CATEGORY_NOT_FOUND", "message": "Specified category does not exist."}
                )
        product.category_id = req.category_id

    if req.unit is not None:
        product.unit = req.unit.strip().lower()

    if req.purchase_cost is not None:
        product.purchase_cost = req.purchase_cost

    if req.selling_price is not None:
        product.selling_price = req.selling_price

    if req.low_stock_threshold is not None:
        product.low_stock_threshold = req.low_stock_threshold

    if req.is_active is not None:
        product.is_active = req.is_active

    db.commit()
    db.refresh(product)
    return product


def toggle_product_status(
    db: Session,
    business_id: uuid.UUID,
    product_id: uuid.UUID,
    is_active: bool
) -> Product:
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.business_id == business_id)
        .first()
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PRODUCT_NOT_FOUND", "message": "Product not found."}
        )
    product.is_active = is_active
    db.commit()
    db.refresh(product)
    return product


def list_products(
    db: Session,
    business_id: uuid.UUID,
    search: Optional[str] = None,
    category_id: Optional[uuid.UUID] = None,
    is_active: Optional[bool] = None,
    low_stock: Optional[bool] = None,
    sort_by: str = "created_at",
    order: str = "desc",
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[dict], int]:
    warehouse = get_default_warehouse(db, business_id)

    query = (
        db.query(
            Product,
            Category.name.label("category_name"),
            func.coalesce(InventoryBalance.current_stock, Decimal("0.0000")).label("current_stock")
        )
        .outerjoin(Category, and_(Category.id == Product.category_id, Category.business_id == business_id))
        .outerjoin(
            InventoryBalance,
            and_(
                InventoryBalance.product_id == Product.id,
                InventoryBalance.warehouse_id == warehouse.id
            )
        )
        .filter(Product.business_id == business_id)
    )

    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(Product.name).ilike(s),
                func.lower(Product.sku).ilike(s),
                func.lower(Product.description).ilike(s),
                func.lower(Product.tamil_name).ilike(s)
            )
        )

    if category_id:
        query = query.filter(Product.category_id == category_id)

    if is_active is not None:
        query = query.filter(Product.is_active == is_active)

    if low_stock is True:
        query = query.filter(
            and_(
                Product.low_stock_threshold > 0,
                func.coalesce(InventoryBalance.current_stock, Decimal("0.0000")) <= Product.low_stock_threshold
            )
        )

    total_count = query.count()

    # Sort
    order_func = desc if order.lower() == "desc" else asc
    if sort_by == "name":
        query = query.order_by(order_func(Product.name))
    elif sort_by == "selling_price":
        query = query.order_by(order_func(Product.selling_price))
    elif sort_by == "current_stock":
        query = query.order_by(order_func(func.coalesce(InventoryBalance.current_stock, Decimal("0.0000"))))
    else:
        query = query.order_by(order_func(Product.created_at))

    items = query.offset(offset).limit(limit).all()

    results = []
    for product, cat_name, cur_stock in items:
        # Determine stock status
        if cur_stock <= Decimal("0.0000"):
            status_str = "out_of_stock"
        elif product.low_stock_threshold > 0 and cur_stock <= product.low_stock_threshold:
            status_str = "low_stock"
        else:
            status_str = "in_stock"

        results.append({
            "id": product.id,
            "business_id": product.business_id,
            "category_id": product.category_id,
            "category_name": cat_name,
            "name": product.name,
            "tamil_name": product.tamil_name,
            "description": product.description,
            "sku": product.sku,
            "unit": product.unit,
            "purchase_cost": product.purchase_cost,
            "selling_price": product.selling_price,
            "low_stock_threshold": product.low_stock_threshold,
            "current_stock": cur_stock,
            "stock_status": status_str,
            "is_active": product.is_active,
            "created_at": product.created_at,
            "updated_at": product.updated_at
        })

    return results, total_count


def get_product_detail(
    db: Session,
    business_id: uuid.UUID,
    product_id: uuid.UUID
) -> dict:
    warehouse = get_default_warehouse(db, business_id)

    item = (
        db.query(
            Product,
            Category.name.label("category_name"),
            func.coalesce(InventoryBalance.current_stock, Decimal("0.0000")).label("current_stock")
        )
        .outerjoin(Category, and_(Category.id == Product.category_id, Category.business_id == business_id))
        .outerjoin(
            InventoryBalance,
            and_(
                InventoryBalance.product_id == Product.id,
                InventoryBalance.warehouse_id == warehouse.id
            )
        )
        .filter(Product.id == product_id, Product.business_id == business_id)
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PRODUCT_NOT_FOUND", "message": "Product not found."}
        )

    product, cat_name, cur_stock = item

    if cur_stock <= Decimal("0.0000"):
        status_str = "out_of_stock"
    elif product.low_stock_threshold > 0 and cur_stock <= product.low_stock_threshold:
        status_str = "low_stock"
    else:
        status_str = "in_stock"

    # Fetch recent movements
    movements_raw = (
        db.query(StockMovement, User.full_name.label("user_name"))
        .outerjoin(User, User.id == StockMovement.created_by_user_id)
        .filter(StockMovement.product_id == product_id, StockMovement.business_id == business_id)
        .order_by(StockMovement.created_at.desc())
        .limit(20)
        .all()
    )

    movements = []
    for mov, user_name in movements_raw:
        movements.append({
            "id": mov.id,
            "business_id": mov.business_id,
            "warehouse_id": mov.warehouse_id,
            "product_id": mov.product_id,
            "product_name": product.name,
            "movement_type": mov.movement_type,
            "quantity_delta": mov.quantity_delta,
            "balance_after": mov.balance_after,
            "unit_cost": mov.unit_cost,
            "reason": mov.reason,
            "created_by_user_id": mov.created_by_user_id,
            "created_by_user_name": user_name,
            "created_at": mov.created_at
        })

    return {
        "id": product.id,
        "business_id": product.business_id,
        "category_id": product.category_id,
        "category_name": cat_name,
        "name": product.name,
        "tamil_name": product.tamil_name,
        "description": product.description,
        "sku": product.sku,
        "unit": product.unit,
        "purchase_cost": product.purchase_cost,
        "selling_price": product.selling_price,
        "low_stock_threshold": product.low_stock_threshold,
        "current_stock": cur_stock,
        "stock_status": status_str,
        "is_active": product.is_active,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
        "recent_movements": movements
    }


# ==========================================
# STOCK ADJUSTMENT & INVENTORY CONTROL
# ==========================================

def adjust_stock(
    db: Session,
    business_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    req: StockAdjustmentCreate
) -> StockMovement:
    """
    Executes a concurrency-safe atomic stock adjustment within a database transaction.
    Locks the inventory balance record with pessimistic row-locking (with_for_update).
    Rejects stock decrease if insufficient balance exists (strict non-negative stock policy).
    """
    warehouse = get_default_warehouse(db, business_id)

    # 1. Verify product exists and belongs to business
    product = (
        db.query(Product)
        .filter(Product.id == req.product_id, Product.business_id == business_id)
        .first()
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PRODUCT_NOT_FOUND", "message": "Product not found."}
        )

    # 2. Pessimistic row locking on InventoryBalance
    balance = (
        db.query(InventoryBalance)
        .filter(
            InventoryBalance.warehouse_id == warehouse.id,
            InventoryBalance.product_id == req.product_id,
            InventoryBalance.business_id == business_id
        )
        .with_for_update()
        .first()
    )

    if not balance:
        balance = InventoryBalance(
            business_id=business_id,
            warehouse_id=warehouse.id,
            product_id=req.product_id,
            current_stock=Decimal("0.0000"),
            reserved_stock=Decimal("0.0000"),
            average_cost=product.purchase_cost
        )
        db.add(balance)
        db.flush()

    # 3. Calculate adjustment delta and validate non-negative stock
    if req.adjustment_type == "increase":
        delta = req.quantity
        movement_type = "adjustment_increase"
        # Moving average cost adjustment if cost is provided
        if req.unit_cost is not None and req.unit_cost > 0:
            total_current_value = balance.current_stock * balance.average_cost
            incoming_value = delta * req.unit_cost
            new_total_qty = balance.current_stock + delta
            if new_total_qty > 0:
                balance.average_cost = (total_current_value + incoming_value) / new_total_qty
    elif req.adjustment_type == "decrease":
        delta = -req.quantity
        movement_type = "adjustment_decrease"
        if balance.current_stock < req.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INSUFFICIENT_STOCK",
                    "message": f"Cannot decrease stock by {req.quantity} {product.unit}. Current stock balance is {balance.current_stock} {product.unit}.",
                    "field": "quantity",
                    "current_stock": str(balance.current_stock)
                }
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_ADJUSTMENT_TYPE", "message": "Adjustment type must be 'increase' or 'decrease'."}
        )

    new_balance = balance.current_stock + delta
    balance.current_stock = new_balance

    # 4. Record stock movement
    cost_to_log = req.unit_cost if req.unit_cost is not None else balance.average_cost
    movement = StockMovement(
        business_id=business_id,
        warehouse_id=warehouse.id,
        product_id=req.product_id,
        movement_type=movement_type,
        quantity_delta=delta,
        balance_after=new_balance,
        unit_cost=cost_to_log,
        reason=req.reason.strip(),
        created_by_user_id=user_id
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement


def list_stock_movements(
    db: Session,
    business_id: uuid.UUID,
    product_id: Optional[uuid.UUID] = None,
    movement_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[dict], int]:
    query = (
        db.query(
            StockMovement,
            Product.name.label("product_name"),
            User.full_name.label("user_name")
        )
        .join(Product, Product.id == StockMovement.product_id)
        .outerjoin(User, User.id == StockMovement.created_by_user_id)
        .filter(StockMovement.business_id == business_id)
    )

    if product_id:
        query = query.filter(StockMovement.product_id == product_id)
    if movement_type:
        query = query.filter(StockMovement.movement_type == movement_type)

    total_count = query.count()
    items = query.order_by(StockMovement.created_at.desc()).offset(offset).limit(limit).all()

    results = []
    for mov, prod_name, user_name in items:
        results.append({
            "id": mov.id,
            "business_id": mov.business_id,
            "warehouse_id": mov.warehouse_id,
            "product_id": mov.product_id,
            "product_name": prod_name,
            "movement_type": mov.movement_type,
            "quantity_delta": mov.quantity_delta,
            "balance_after": mov.balance_after,
            "unit_cost": mov.unit_cost,
            "reason": mov.reason,
            "created_by_user_id": mov.created_by_user_id,
            "created_by_user_name": user_name,
            "created_at": mov.created_at
        })

    return results, total_count


def get_inventory_overview(db: Session, business_id: uuid.UUID) -> dict:
    warehouse = get_default_warehouse(db, business_id)

    total_products = db.query(Product).filter(Product.business_id == business_id).count()
    active_products = db.query(Product).filter(Product.business_id == business_id, Product.is_active == True).count()
    total_categories = db.query(Category).filter(Category.business_id == business_id, Category.is_active == True).count()

    # Query balances joined with product
    items = (
        db.query(
            Product.low_stock_threshold,
            Product.purchase_cost,
            func.coalesce(InventoryBalance.current_stock, Decimal("0.0000")).label("current_stock"),
            func.coalesce(InventoryBalance.average_cost, Product.purchase_cost).label("cost")
        )
        .outerjoin(
            InventoryBalance,
            and_(
                InventoryBalance.product_id == Product.id,
                InventoryBalance.warehouse_id == warehouse.id
            )
        )
        .filter(Product.business_id == business_id, Product.is_active == True)
        .all()
    )

    low_stock_count = 0
    out_of_stock_count = 0
    total_stock_value = Decimal("0.0000")

    for threshold, purchase_cost, cur_stock, cost in items:
        if cur_stock <= Decimal("0.0000"):
            out_of_stock_count += 1
        elif threshold > 0 and cur_stock <= threshold:
            low_stock_count += 1

        if cur_stock > 0:
            effective_cost = cost if cost > 0 else purchase_cost
            total_stock_value += (cur_stock * effective_cost)

    return {
        "total_products": total_products,
        "active_products": active_products,
        "low_stock_products": low_stock_count,
        "out_of_stock_products": out_of_stock_count,
        "total_stock_value": total_stock_value,
        "total_categories": total_categories
    }
