import pytest
from app.services.recommendation import calculate_recommendation, AVAILABLE_MODULES


def test_recommendation_single_user_single_branch_retail():
    """
    Scenario: A neighborhood kirana / retail store with 1 counter user and 1 branch.
    Expected: Kanakku Simple.
    """
    answers = {
        "business_name": "Murugan Stores",
        "category": "grocery",
        "workforce_count": 2,
        "app_users_count": 1,
        "branch_count": 1,
        "warehouse_count": 1,
        "operations": ["retail"],
        "tracks_inventory": True,
        "purchase_orders": False,
        "has_manufacturing": False,
        "track_customer_credit": True,
        "track_supplier_payments": False,
        "need_staff_permissions": False,
        "need_approval_workflows": False,
    }
    rec = calculate_recommendation(answers)
    assert rec["recommended_tier"] == "simple"
    assert "pos_billing" in rec["recommended_modules"]
    assert "simple_inventory" in rec["recommended_modules"]
    assert "customer_khata" in rec["recommended_modules"]
    # Check that reasons contain SINGLE_OPERATOR and SINGLE_LOCATION
    codes = [r["code"] for r in rec["reasons"]]
    assert "SINGLE_OPERATOR" in codes
    assert "SINGLE_LOCATION" in codes


def test_recommendation_large_workforce_single_counter_not_forced_enterprise():
    """
    Scenario: A busy textile shop or restaurant kitchen with 25 manual workers
    but only 1 counter app user and 1 outlet.
    Crucial requirement: Employee count alone must NOT dictate the tier!
    Expected: Remains Simple (or Growth if wholesale), NOT Enterprise.
    """
    answers = {
        "business_name": "Cauvery Handlooms",
        "category": "textile",
        "workforce_count": 25,
        "app_users_count": 1,
        "branch_count": 1,
        "warehouse_count": 1,
        "operations": ["retail"],
        "tracks_inventory": True,
        "purchase_orders": False,
        "has_manufacturing": False,
        "track_customer_credit": False,
        "track_supplier_payments": False,
        "need_staff_permissions": False,
        "need_approval_workflows": False,
    }
    rec = calculate_recommendation(answers)
    assert rec["recommended_tier"] == "simple"
    codes = [r["code"] for r in rec["reasons"]]
    assert "HEADCOUNT_INDEPENDENCE" in codes


def test_recommendation_growing_multi_branch_wholesale():
    """
    Scenario: A wholesale distributor with 3 branches, 5 users, and supplier payables.
    Expected: Kanakku Growth.
    """
    answers = {
        "business_name": "Madurai Wholesale Traders",
        "category": "fmcg",
        "workforce_count": 12,
        "app_users_count": 5,
        "branch_count": 3,
        "warehouse_count": 2,
        "operations": ["wholesale", "retail"],
        "tracks_inventory": True,
        "purchase_orders": True,
        "has_manufacturing": False,
        "track_customer_credit": True,
        "track_supplier_payments": True,
        "need_staff_permissions": True,
        "need_approval_workflows": False,
    }
    rec = calculate_recommendation(answers)
    assert rec["recommended_tier"] == "growth"
    assert "supplier_payables" in rec["recommended_modules"]
    assert "purchase_orders" in rec["recommended_modules"]
    assert "role_permissions" in rec["recommended_modules"]
    codes = [r["code"] for r in rec["reasons"]]
    assert "MULTI_BRANCH_GROWTH" in codes
    assert "WHOLESALE_DISCOUNTS" in codes


def test_recommendation_manufacturing_raw_materials():
    """
    Scenario: A packaging unit or bakery that manages raw materials,
    batches, and wastage.
    Expected: Kanakku Growth or Enterprise with manufacturing BOM module.
    """
    answers = {
        "business_name": "Lakshmi Sweets & Bakery",
        "category": "bakery",
        "workforce_count": 8,
        "app_users_count": 2,
        "branch_count": 1,
        "warehouse_count": 1,
        "operations": ["manufacturing", "retail"],
        "tracks_inventory": True,
        "purchase_orders": True,
        "has_manufacturing": True,
        "raw_materials": True,
        "production_batches": True,
        "scrap_wastage": True,
        "track_customer_credit": False,
        "track_supplier_payments": True,
        "need_staff_permissions": False,
        "need_approval_workflows": False,
    }
    rec = calculate_recommendation(answers)
    assert rec["recommended_tier"] in ["growth", "enterprise"]
    assert "manufacturing_bom" in rec["recommended_modules"]


def test_recommendation_enterprise_complex_governance():
    """
    Scenario: Large regional enterprise with 6 branches, 15 app users,
    multi-level approvals, and consolidated governance.
    Expected: Kanakku Enterprise.
    """
    answers = {
        "business_name": "Kongu Retail Networks",
        "category": "electronics",
        "workforce_count": 45,
        "app_users_count": 15,
        "branch_count": 6,
        "warehouse_count": 4,
        "operations": ["retail", "wholesale"],
        "tracks_inventory": True,
        "purchase_orders": True,
        "has_manufacturing": False,
        "track_customer_credit": True,
        "track_supplier_payments": True,
        "need_staff_permissions": True,
        "need_approval_workflows": True,
    }
    rec = calculate_recommendation(answers)
    assert rec["recommended_tier"] == "enterprise"
    assert "multi_warehouse" in rec["recommended_modules"]
    assert "approval_workflows" in rec["recommended_modules"]
    assert "consolidated_analytics" in rec["recommended_modules"]
    codes = [r["code"] for r in rec["reasons"]]
    assert "ENTERPRISE_USER_SCALE" in codes
    assert "ENTERPRISE_DISTRIBUTION" in codes


def test_recommendation_is_deterministic():
    """
    Identical questionnaire answers must always yield identical recommendations.
    """
    answers = {
        "workforce_count": 5,
        "app_users_count": 3,
        "branch_count": 2,
        "operations": ["retail"],
        "tracks_inventory": True,
    }
    rec1 = calculate_recommendation(answers)
    rec2 = calculate_recommendation(answers)
    assert rec1 == rec2
    assert rec1["complexity_score"] == rec2["complexity_score"]
    assert rec1["recommended_tier"] == rec2["recommended_tier"]


# =========================================================================
# API Integration Tests for Drafts, Resuming, Completion, and Isolation
# =========================================================================

def test_onboarding_lifecycle_and_draft_persistence(client):
    """
    Tests registering an owner, getting onboarding state, saving step drafts,
    resuming after refresh, and completing onboarding with owner override.
    """
    # 1. Register owner
    reg_res = client.post("/api/v1/auth/register", json={
        "phone": "9876511111",
        "pin_or_password": "887766",
        "full_name": "Senthil Nathan",
        "business_name": "Senthil Auto Spares",
        "default_language": "ta"
    })
    assert reg_res.status_code == 201
    token = reg_res.json()["data"]["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Check initial onboarding state
    state_res = client.get("/api/v1/onboarding", headers=headers)
    assert state_res.status_code == 200
    state = state_res.json()["data"]
    assert state["onboarding_completed"] is False
    assert state["current_step"] == 1
    assert state["business_name"] == "Senthil Auto Spares"

    # 3. Save draft at step 4
    draft_answers = {
        "business_name": "Senthil Auto Parts Pvt Ltd",
        "category": "automotive",
        "workforce_count": 6,
        "app_users_count": 3,
        "branch_count": 2,
        "warehouse_count": 1,
        "operations": ["retail", "wholesale"],
        "tracks_inventory": True,
        "purchase_orders": True,
        "has_manufacturing": False,
        "track_customer_credit": True,
        "track_supplier_payments": True,
        "need_staff_permissions": True,
        "need_approval_workflows": False,
        "preferred_language": "tanglish",
        "accessibility": {"high_contrast": True, "large_font": False, "simplified_ui": False}
    }
    save_res = client.put("/api/v1/onboarding/draft", headers=headers, json={
        "step": 4,
        "answers": draft_answers
    })
    assert save_res.status_code == 200
    saved = save_res.json()["data"]
    assert saved["current_step"] == 4
    assert saved["business_name"] == "Senthil Auto Parts Pvt Ltd"
    assert saved["answers"]["category"] == "automotive"

    # 4. Simulate page refresh / resume: GET /api/v1/onboarding returns saved answers
    resume_res = client.get("/api/v1/onboarding", headers=headers)
    assert resume_res.status_code == 200
    resumed = resume_res.json()["data"]
    assert resumed["current_step"] == 4
    assert resumed["answers"]["branch_count"] == 2
    assert resumed["answers"]["operations"] == ["retail", "wholesale"]

    # 5. Request recommendation calculation via API
    rec_api_res = client.post("/api/v1/onboarding/recommend", headers=headers, json=draft_answers)
    assert rec_api_res.status_code == 200
    rec_data = rec_api_res.json()["data"]
    assert rec_data["recommended_tier"] == "growth"
    assert len(rec_data["reasons"]) > 0

    # 6. Complete onboarding with Owner Override:
    # Recommended was Growth, but owner chooses Enterprise or Simple with custom modules
    complete_res = client.post("/api/v1/onboarding/complete", headers=headers, json={
        "selected_tier": "growth",
        "enabled_modules": ["pos_billing", "simple_inventory", "supplier_payables", "customer_khata"],
        "answers": draft_answers
    })
    assert complete_res.status_code == 200
    completed_profile = complete_res.json()["data"]
    assert completed_profile["onboarding_completed"] is True
    assert completed_profile["tier"] == "growth"
    assert completed_profile["recommended_tier"] == "growth"
    assert completed_profile["workforce_count"] == 6
    assert completed_profile["app_users_count"] == 3
    assert completed_profile["branch_count"] == 2
    assert "pos_billing" in completed_profile["enabled_modules"]

    # 7. Verify /api/v1/business/profile reflects completed state
    prof_res = client.get("/api/v1/business/profile", headers=headers)
    assert prof_res.status_code == 200
    assert prof_res.json()["data"]["onboarding_completed"] is True
    assert prof_res.json()["data"]["name"] == "Senthil Auto Parts Pvt Ltd"

    # 8. Test updating preferences post-onboarding
    pref_res = client.put("/api/v1/business/preferences", headers=headers, json={
        "default_language": "en",
        "accessibility_settings": {"high_contrast": False, "large_font": True, "simplified_ui": True}
    })
    assert pref_res.status_code == 200
    assert pref_res.json()["data"]["default_language"] == "en"
    assert pref_res.json()["data"]["accessibility_settings"]["large_font"] is True


def test_cross_tenant_profile_access_denied(client):
    """
    Validates that tenant A cannot access or update tenant B's onboarding or profile,
    even if supplying Tenant B's ID via headers.
    """
    # Create Tenant A
    res_a = client.post("/api/v1/auth/register", json={
        "phone": "9876522221",
        "pin_or_password": "112233",
        "full_name": "Owner A",
        "business_name": "Store A",
    })
    token_a = res_a.json()["data"]["tokens"]["access_token"]
    biz_a_id = res_a.json()["data"]["business"]["id"]

    # Create Tenant B
    res_b = client.post("/api/v1/auth/register", json={
        "phone": "9876522222",
        "pin_or_password": "112233",
        "full_name": "Owner B",
        "business_name": "Store B",
    })
    token_b = res_b.json()["data"]["tokens"]["access_token"]
    biz_b_id = res_b.json()["data"]["business"]["id"]

    # Tenant A attempts to access Tenant B by setting X-Business-ID header
    bad_req = client.get("/api/v1/business/profile", headers={
        "Authorization": f"Bearer {token_a}",
        "X-Business-ID": biz_b_id
    })
    assert bad_req.status_code == 403
    assert bad_req.json()["error"]["code"] == "CROSS_TENANT_ACCESS_DENIED"
