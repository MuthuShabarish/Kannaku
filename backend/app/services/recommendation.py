"""
Kanakku Rule-Based Recommendation Engine
Stage 2: Deterministic, Explainable Operational Complexity Evaluator

Evaluates business operational complexity across 6 dimensions:
1. Active App Users (concurrency & role segregation)
2. Outlets & Locations (multi-branch coordination)
3. Inventory & Purchasing Depth (moving average cost, purchase orders)
4. Manufacturing & Batch Tracking (BOM, scrap, batches)
5. Credit & Khata Accounting (double-entry customer/vendor ledgers)
6. Governance & Approval Hierarchies (multi-level approvals)

Returns deterministic recommended tier, complexity score, explainable reasons,
and recommended module activations.
"""
from typing import Dict, Any, List, Tuple


AVAILABLE_MODULES = [
    {
        "id": "pos_billing",
        "name_en": "Point of Sale (POS) Billing",
        "name_ta": "விற்பனை ரசீது (POS)",
        "name_tanglish": "POS Billing",
        "description_en": "Fast touch-optimized sales counter and instant receipt generation.",
        "description_ta": "விரைவான விற்பனை மற்றும் உடனடி ரசீது தயாரித்தல்.",
        "description_tanglish": "Fast sales counter and instant receipt generation.",
        "category": "sales",
        "tier": "simple",
    },
    {
        "id": "simple_inventory",
        "name_en": "Fast Inventory Counter",
        "name_ta": "எளிய சரக்கு இருப்பு",
        "name_tanglish": "Simple Inventory",
        "description_en": "Current stock count, low-stock alerts, and manual adjustments.",
        "description_ta": "தற்போதைய இருப்பு மற்றும் குறைவு எச்சரிக்கை.",
        "description_tanglish": "Stock count and low-stock alerts.",
        "category": "inventory",
        "tier": "simple",
    },
    {
        "id": "customer_khata",
        "name_en": "Customer Credit (Khata / Udhar)",
        "name_ta": "வாடிக்கையாளர் கடன் கணக்கு (காதா)",
        "name_tanglish": "Customer Credit (Khata)",
        "description_en": "Customer balances, payment reminders, and credit limits.",
        "description_ta": "கடன் இருப்பு மற்றும் நினைவூட்டல்.",
        "description_tanglish": "Customer balances and credit limits.",
        "category": "credit",
        "tier": "simple",
    },
    {
        "id": "supplier_payables",
        "name_en": "Supplier Bills & Payables",
        "name_ta": "சப்ளையர் பில்கள் மற்றும் நிலுவை",
        "name_tanglish": "Supplier Bills & Payables",
        "description_en": "Track vendor purchase invoices and payment schedules.",
        "description_ta": "சப்ளையர் கொள்முதல் மற்றும் கட்டண காலக்கெடு.",
        "description_tanglish": "Vendor purchase invoices and payments.",
        "category": "purchases",
        "tier": "growth",
    },
    {
        "id": "purchase_orders",
        "name_en": "Purchase Orders & Goods Receipt",
        "name_ta": "கொள்முதல் ஆணைகள் (PO)",
        "name_tanglish": "Purchase Orders (PO)",
        "description_en": "Formal purchase orders and goods receipt notes (GRN).",
        "description_ta": "கொள்முதல் ஆணைகள் மற்றும் சரக்கு வரவு ரசீதுகள்.",
        "description_tanglish": "Purchase orders and goods receipt.",
        "category": "purchases",
        "tier": "growth",
    },
    {
        "id": "batch_tracking",
        "name_en": "Batch & Expiry Management",
        "name_ta": "பேட்ச் மற்றும் காலாவதி மேலாண்மை",
        "name_tanglish": "Batch & Expiry Management",
        "description_en": "Batch numbers, manufacturing dates, and expiration alerts.",
        "description_ta": "பேட்ச் எண்கள் மற்றும் காலாவதி கண்காணிப்பு.",
        "description_tanglish": "Batch numbers and expiry dates.",
        "category": "inventory",
        "tier": "growth",
    },
    {
        "id": "gst_tax_reports",
        "name_en": "GST & Tax Filing Reports",
        "name_ta": "ஜிஎஸ்டி மற்றும் வரி அறிக்கைகள்",
        "name_tanglish": "GST & Tax Reports",
        "description_en": "GSTR-1, GSTR-3B summaries and HSN-wise tax breakdown.",
        "description_ta": "ஜிஎஸ்டி சுருக்கங்கள் மற்றும் எச்எஸ்என் வரி அறிக்கை.",
        "description_tanglish": "GSTR summaries and tax breakdown.",
        "category": "reports",
        "tier": "growth",
    },
    {
        "id": "multi_warehouse",
        "name_en": "Multi-Warehouse Stock Transfer",
        "name_ta": "பல கிடங்கு சரக்கு பரிமாற்றம்",
        "name_tanglish": "Multi-Warehouse Transfer",
        "description_en": "Inter-branch stock transfers and warehouse logistics.",
        "description_ta": "கிளைகளுக்கிடையேயான சரக்கு பரிமாற்றங்கள்.",
        "description_tanglish": "Inter-branch stock transfers and warehouses.",
        "category": "inventory",
        "tier": "enterprise",
    },
    {
        "id": "manufacturing_bom",
        "name_en": "Manufacturing & Bill of Materials (BOM)",
        "name_ta": "உற்பத்தி மற்றும் மூலப்பொருள் கணக்கு",
        "name_tanglish": "Manufacturing & BOM",
        "description_en": "Raw material recipes, production batches, and scrap/wastage accounting.",
        "description_ta": "மூலப்பொருட்கள், உற்பத்தி தொகுதிகள் மற்றும் கழிவு கணக்கு.",
        "description_tanglish": "Raw material recipes, batches, and scrap accounting.",
        "category": "manufacturing",
        "tier": "enterprise",
    },
    {
        "id": "approval_workflows",
        "name_en": "Multi-Level Approvals & Audit Trail",
        "name_ta": "அனுமதி நெறிமுறைகள் & தணிக்கை பதிவு",
        "name_tanglish": "Approvals & Audit Trail",
        "description_en": "Manager overrides, purchase approval limits, and tamper-evident audit logs.",
        "description_ta": "மேலாளர் அனுமதிகள் மற்றும் தணிக்கை பதிவுகள்.",
        "description_tanglish": "Manager overrides and audit logs.",
        "category": "governance",
        "tier": "enterprise",
    },
    {
        "id": "role_permissions",
        "name_en": "Granular Staff Roles & Permissions",
        "name_ta": "பணியாளர் அனுமதிகள் & பாத்திரங்கள்",
        "name_tanglish": "Staff Roles & Permissions",
        "description_en": "Custom role privileges for cashiers, store managers, and accountants.",
        "description_ta": "காசாளர், மேலாளர் மற்றும் கணக்காளர் தனிப்பயன் அனுமதிகள்.",
        "description_tanglish": "Custom role privileges for cashiers and managers.",
        "category": "governance",
        "tier": "growth",
    },
    {
        "id": "consolidated_analytics",
        "name_en": "Consolidated Multi-Branch Analytics",
        "name_ta": "ஒருங்கிணைந்த கிளை பகுப்பாய்வு",
        "name_tanglish": "Consolidated Branch Analytics",
        "description_en": "Unified cross-branch P&L, balance sheets, and executive KPI dashboards.",
        "description_ta": "அனைத்து கிளைகளின் ஒருங்கிணைந்த லாப-நஷ்ட கணக்கு.",
        "description_tanglish": "Unified cross-branch P&L and dashboards.",
        "category": "reports",
        "tier": "enterprise",
    },
]


def calculate_recommendation(answers: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic evaluation of business onboarding answers.
    Returns:
    - recommended_tier: 'simple' | 'growth' | 'enterprise'
    - complexity_score: 0-100
    - reasons: List of explainable reasoning points
    - recommended_modules: List of module string IDs
    """
    # Extract values with safe defaults
    app_users = int(answers.get("app_users_count") or 1)
    workforce = int(answers.get("workforce_count") or 1)
    branches = int(answers.get("branch_count") or 1)
    warehouses = int(answers.get("warehouse_count") or 1)
    operations = answers.get("operations") or ["retail"]
    if isinstance(operations, str):
        operations = [operations]
    
    tracks_inventory = bool(answers.get("tracks_inventory", True))
    purchase_orders = bool(answers.get("purchase_orders", False))
    has_manufacturing = "manufacturing" in operations or bool(answers.get("has_manufacturing", False))
    raw_materials = bool(answers.get("raw_materials", False))
    production_batches = bool(answers.get("production_batches", False))
    scrap_wastage = bool(answers.get("scrap_wastage", False))
    
    track_customer_credit = bool(answers.get("track_customer_credit", False))
    track_supplier_payments = bool(answers.get("track_supplier_payments", False))
    need_staff_permissions = bool(answers.get("need_staff_permissions", False))
    need_approval_workflows = bool(answers.get("need_approval_workflows", False))

    reasons: List[Dict[str, str]] = []
    complexity_score = 10  # Base score

    # 1. User Concurrency & Delegation
    if app_users == 1:
        complexity_score += 0
        reasons.append({
            "code": "SINGLE_OPERATOR",
            "title_en": "Single Operator Focus",
            "title_ta": "தனிநபர் நேரடி பயன்பாடு",
            "title_tanglish": "Single Operator Focus",
            "desc_en": "A single person operates the software, eliminating multi-user permission overhead.",
            "desc_ta": "ஒருவரே மென்பொருளைப் பயன்படுத்துவதால் கூடுதல் பயனர் அனுமதி தேவையில்லை.",
            "desc_tanglish": "Single person operates the software with zero permission overhead.",
        })
    elif 2 <= app_users <= 5:
        complexity_score += 15
        reasons.append({
            "code": "SMALL_TEAM_ROLES",
            "title_en": "Small Team Role Division",
            "title_ta": "சிறிய குழு பணிப்பிரிவு",
            "title_tanglish": "Small Team Role Division",
            "desc_en": f"{app_users} team members share software operations, benefiting from cashier and manager separation.",
            "desc_ta": f"{app_users} பணியாளர்கள் பயன்பாட்டைப் பகிர்வதால் காசாளர் மற்றும் மேலாளர் பிரிவுகள் தேவை.",
            "desc_tanglish": f"{app_users} team members benefit from cashier and manager role separation.",
        })
    elif 6 <= app_users <= 10:
        complexity_score += 25
        reasons.append({
            "code": "GROWING_WORKFORCE",
            "title_en": "Growing Team Coordination",
            "title_ta": "வளரும் குழு ஒருங்கிணைப்பு",
            "title_tanglish": "Growing Team Coordination",
            "desc_en": f"{app_users} active software users require structured user permissions and shift handovers.",
            "desc_ta": f"{app_users} மென்பொருள் பயனர்களுக்கு தனித்தனி அனுமதிகள் மற்றும் ஷிப்ட் கணக்குகள் தேவை.",
            "desc_tanglish": f"{app_users} active users require structured permissions and shift handovers.",
        })
    else:  # > 10 users
        complexity_score += 35
        reasons.append({
            "code": "ENTERPRISE_USER_SCALE",
            "title_en": "Large Team Multi-User Scale",
            "title_ta": "பெரிய குழு பயனர்கள்",
            "title_tanglish": "Large Team Multi-User Scale",
            "desc_en": f"Over 10 active application users ({app_users}) require enterprise role hierarchies and access controls.",
            "desc_ta": f"10-க்கும் மேற்பட்ட பயனர்கள் ({app_users}) உள்ளதால் விரிவான அனுமதிகள் தேவை.",
            "desc_tanglish": f"Over 10 active users ({app_users}) require enterprise role hierarchies.",
        })

    # Note: Employee count alone does not dictate tier
    if workforce > 20 and app_users <= 2:
        reasons.append({
            "code": "HEADCOUNT_INDEPENDENCE",
            "title_en": "Field Headcount vs Counter Users",
            "title_ta": "களப் பணியாளர்கள் மற்றும் காண்டர் பயன்பாடு",
            "title_tanglish": "Field Headcount vs Counter Users",
            "desc_en": f"Your workforce of {workforce} workers does not force complex software, keeping counter billing lightning fast.",
            "desc_ta": f"{workforce} பணியாளர்கள் இருந்தாலும் காண்டர் பயன்பாடு எளிய முறையில் விரைவாக இயங்கும்.",
            "desc_tanglish": f"Workforce of {workforce} kept simple for lightning fast billing.",
        })

    # 2. Locations & Warehouses
    if branches == 1 and warehouses <= 1:
        reasons.append({
            "code": "SINGLE_LOCATION",
            "title_en": "Single Outlet Simplicity",
            "title_ta": "ஒற்றைக் கடை எளிமை",
            "title_tanglish": "Single Outlet Simplicity",
            "desc_en": "Operating a single counter or branch allows maximum speed with zero inter-branch complexity.",
            "desc_ta": "ஒற்றைக் கடை என்பதால் கிளைகளுக்கிடையேயான சிக்கலின்றி மிக விரைவாக இயங்கும்.",
            "desc_tanglish": "Operating a single outlet allows maximum speed with zero multi-branch complexity.",
        })
    elif 2 <= branches <= 4 or warehouses == 2:
        complexity_score += 20
        reasons.append({
            "code": "MULTI_BRANCH_GROWTH",
            "title_en": "Multi-Branch Operations",
            "title_ta": "பல கிளைகள் மேலாண்மை",
            "title_tanglish": "Multi-Branch Operations",
            "desc_en": f"Coordinating {branches} branches and {warehouses} warehouses requires multi-location stock tracking.",
            "desc_ta": f"{branches} கிளைகள் மற்றும் {warehouses} கிடங்குகளைக் கண்காணிக்க பல இட சரக்கு மேலாண்மை தேவை.",
            "desc_tanglish": f"Coordinating {branches} branches and {warehouses} warehouses requires multi-location tracking.",
        })
    else:  # > 4 branches or > 2 warehouses
        complexity_score += 35
        reasons.append({
            "code": "ENTERPRISE_DISTRIBUTION",
            "title_en": "Extensive Multi-Branch Network",
            "title_ta": "விரிவான பல கிளை வலையமைப்பு",
            "title_tanglish": "Extensive Multi-Branch Network",
            "desc_en": f"{branches} branches and {warehouses} warehouses demand enterprise transfer logistics and centralized controls.",
            "desc_ta": f"{branches} கிளைகளுக்கு மத்திய கட்டுப்பாட்டுடன் கூடிய சரக்கு பரிமாற்றம் அவசியம்.",
            "desc_tanglish": f"{branches} branches demand enterprise transfer logistics and centralized controls.",
        })

    # 3. Operational Model & Wholesale
    if "wholesale" in operations:
        complexity_score += 15
        reasons.append({
            "code": "WHOLESALE_DISCOUNTS",
            "title_en": "Wholesale Price Tiers & Invoicing",
            "title_ta": "மொத்த விற்பனை விலைப்பட்டியல்",
            "title_tanglish": "Wholesale Price Tiers",
            "desc_en": "Wholesale operations require tiered customer pricing, bulk billing, and tax invoice generation.",
            "desc_ta": "மொத்த விற்பனைக்கு தொகுதி விலைப்பட்டியல் மற்றும் வரி ரசீதுகள் தேவை.",
            "desc_tanglish": "Wholesale operations require tiered pricing and bulk billing.",
        })

    # 4. Manufacturing & Batch Tracking
    if has_manufacturing or raw_materials or production_batches:
        if raw_materials and production_batches and scrap_wastage:
            complexity_score += 35
            reasons.append({
                "code": "FULL_MANUFACTURING_BOM",
                "title_en": "Advanced Manufacturing & Recipe Costing",
                "title_ta": "முழு உற்பத்தி மற்றும் மூலப்பொருள் கணக்கு",
                "title_tanglish": "Advanced Manufacturing & BOM",
                "desc_en": "Tracking raw materials, production batches, and scrap/wastage requires full Bill of Materials (BOM) management.",
                "desc_ta": "மூலப்பொருட்கள், உற்பத்தி தொகுதிகள் மற்றும் கழிவு கணக்கீடுக்கு முழு உற்பத்தி தொகுதி தேவை.",
                "desc_tanglish": "Tracking raw materials, batches, and scrap requires full Bill of Materials management.",
            })
        else:
            complexity_score += 20
            reasons.append({
                "code": "LIGHT_MANUFACTURING",
                "title_en": "Assembly / Batch Production",
                "title_ta": "தொகுதி தயாரிப்பு",
                "title_tanglish": "Batch Production",
                "desc_en": "Production batch tracking is needed to trace input materials into finished goods.",
                "desc_ta": "உற்பத்தி தொகுதிகளைக் கண்காணிக்க தொகுதி மேலாண்மை தேவை.",
                "desc_tanglish": "Production batch tracking needed to trace materials into finished goods.",
            })

    # 5. Inventory & Purchasing
    if tracks_inventory and purchase_orders:
        complexity_score += 15
        reasons.append({
            "code": "PURCHASE_MANAGEMENT",
            "title_en": "Structured Purchasing & Reordering",
            "title_ta": "முறைப்படுத்தப்பட்ட கொள்முதல்",
            "title_tanglish": "Structured Purchasing",
            "desc_en": "Generating purchase orders and reconciling goods received protects against supplier overbilling.",
            "desc_ta": "சப்ளையர் கொள்முதல் ஆணைகள் மற்றும் சரக்கு சரிபார்ப்பு அவசியம்.",
            "desc_tanglish": "Generating POs and goods receipt protects against supplier overbilling.",
        })
    elif not tracks_inventory:
        reasons.append({
            "code": "ZERO_STOCK_OVERHEAD",
            "title_en": "Service / Immediate Turnaround",
            "title_ta": "சரக்கு இருப்பு இல்லாத நேரடி சேவை",
            "title_tanglish": "Service / Immediate Turnaround",
            "desc_en": "No inventory tracking needed, keeping screens uncluttered for pure service and billing speed.",
            "desc_ta": "சரக்கு இருப்பு கணக்கு தேவையில்லை என்பதால் திரை மிகவும் எளிமையாக இருக்கும்.",
            "desc_tanglish": "No stock tracking needed, keeping screens uncluttered.",
        })

    # 6. Credit & Supplier Accounting
    if track_customer_credit and track_supplier_payments:
        complexity_score += 15
        reasons.append({
            "code": "DUAL_CREDIT_LEDGER",
            "title_en": "Comprehensive Credit Ledgers",
            "title_ta": "வாடிக்கையாளர் & சப்ளையர் கடன் கணக்கு",
            "title_tanglish": "Comprehensive Credit Ledgers",
            "desc_en": "Tracking customer credit (Udhar) and supplier payables requires double-entry ledger bookkeeping.",
            "desc_ta": "வாடிக்கையாளர் கடன் மற்றும் சப்ளையர் நிலுவை இரண்டையும் கண்காணிக்க விரிவான பேரேடு தேவை.",
            "desc_tanglish": "Tracking customer credit and supplier payables requires ledger bookkeeping.",
        })
    elif track_customer_credit:
        complexity_score += 8
        reasons.append({
            "code": "CUSTOMER_KHATA_ONLY",
            "title_en": "Customer Khata Management",
            "title_ta": "வாடிக்கையாளர் கடன் கணக்கு",
            "title_tanglish": "Customer Khata",
            "desc_en": "Simple customer credit book keeps track of trusted regulars without heavy accounting overhead.",
            "desc_ta": "வாடிக்கையாளர் கடன் கணக்கு எளிதாகப் பராமரிக்கப்படும்.",
            "desc_tanglish": "Simple customer credit book tracks regular customers easily.",
        })

    # 7. Approvals & Permissions
    if need_approval_workflows:
        complexity_score += 25
        reasons.append({
            "code": "APPROVAL_GOVERNANCE",
            "title_en": "Multi-Level Approvals & Audit Trail",
            "title_ta": "பல அடுக்கு அனுமதிகள் & தணிக்கை",
            "title_tanglish": "Approvals & Audit Trail",
            "desc_en": "Requirement for supervisor approvals on discounts, voids, and purchase budgets demands enterprise governance.",
            "desc_ta": "தள்ளுபடி மற்றும் ரத்து செய்வதற்கு மேற்பார்வையாளர் அனுமதி தேவைப்படுவதால் தணிக்கை நெறிமுறை அவசியம்.",
            "desc_tanglish": "Supervisor approvals on discounts and voids demand enterprise governance.",
        })
    elif need_staff_permissions:
        complexity_score += 12
        reasons.append({
            "code": "ROLE_BASED_PERMISSIONS",
            "title_en": "Staff Role Permissions",
            "title_ta": "பணியாளர் அனுமதி கட்டுப்பாடுகள்",
            "title_tanglish": "Staff Role Permissions",
            "desc_en": "Preventing staff from seeing sensitive profit margins while allowing daily sales entries.",
            "desc_ta": "பணியாளர்கள் லாப விபரங்களை பார்க்காமல் விற்பனை செய்ய மட்டும் அனுமதிக்கும் கட்டுப்பாடு.",
            "desc_tanglish": "Preventing staff from seeing profit margins while allowing sales entries.",
        })

    # Clamp complexity score
    complexity_score = min(max(complexity_score, 10), 100)

    # 8. Tier Decision
    # Enterprise Conditions:
    # 1. High user scale (app_users > 10)
    # 2. Or large distributed branch network (branches > 4 or warehouses > 3)
    # 3. Or formal approval workflows with multi-user or multi-branch hierarchy
    # 4. Or full manufacturing with raw materials, batches, and scrap across multi-branch
    is_enterprise = (
        branches > 4
        or warehouses > 3
        or app_users > 10
        or (need_approval_workflows and (branches > 1 or app_users >= 5))
        or (raw_materials and production_batches and scrap_wastage and branches > 1)
        or (complexity_score >= 80 and need_approval_workflows)
    )

    # Growth Conditions:
    # 1. Score between 30 and 64
    # 2. Or branches 2-4
    # 3. Or app_users 3-10
    # 4. Or wholesale
    # 5. Or manufacturing (any)
    # 6. Or dual credit ledger + purchase orders
    # 7. Or staff permissions
    is_growth = (
        not is_enterprise
        and (
            complexity_score >= 30
            or branches >= 2
            or app_users >= 3
            or "wholesale" in operations
            or has_manufacturing
            or raw_materials
            or production_batches
            or (track_customer_credit and track_supplier_payments)
            or need_staff_permissions
            or purchase_orders
        )
    )

    if is_enterprise:
        recommended_tier = "enterprise"
    elif is_growth:
        recommended_tier = "growth"
    else:
        recommended_tier = "simple"

    # 9. Determine Recommended Modules based on tier and answers
    rec_modules: List[str] = ["pos_billing"]

    if tracks_inventory:
        if recommended_tier == "simple":
            rec_modules.append("simple_inventory")
        else:
            rec_modules.append("simple_inventory")
            rec_modules.append("batch_tracking")

    if track_customer_credit:
        rec_modules.append("customer_khata")

    if track_supplier_payments or purchase_orders or recommended_tier in ["growth", "enterprise"]:
        rec_modules.append("supplier_payables")

    if purchase_orders or recommended_tier in ["growth", "enterprise"]:
        rec_modules.append("purchase_orders")

    if "wholesale" in operations or recommended_tier in ["growth", "enterprise"]:
        rec_modules.append("gst_tax_reports")

    if branches > 1 or warehouses > 1 or recommended_tier == "enterprise":
        rec_modules.append("multi_warehouse")
        rec_modules.append("consolidated_analytics")

    if has_manufacturing or raw_materials or production_batches:
        rec_modules.append("manufacturing_bom")

    if need_staff_permissions or recommended_tier in ["growth", "enterprise"]:
        rec_modules.append("role_permissions")

    if need_approval_workflows or recommended_tier == "enterprise":
        rec_modules.append("approval_workflows")

    # Deduplicate module IDs preserving order
    unique_modules = []
    for m in rec_modules:
        if m not in unique_modules:
            unique_modules.append(m)

    return {
        "recommended_tier": recommended_tier,
        "complexity_score": complexity_score,
        "reasons": reasons,
        "recommended_modules": unique_modules,
        "available_modules": AVAILABLE_MODULES,
    }
