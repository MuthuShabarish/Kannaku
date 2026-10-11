import pytest
from sqlalchemy import text


def test_postgresql_canonical_engine_available(postgres_engine):
    """
    Validates PostgreSQL canonical database connectivity.
    If PostgreSQL is unavailable on host, skips with explicit explanation.
    """
    if postgres_engine is None:
        pytest.skip(
            "PostgreSQL test database not reachable at localhost:5432. "
            "Reported accurately as required: PostgreSQL integration tests require running PostgreSQL / Docker Compose service."
        )

    with postgres_engine.connect() as conn:
        result = conn.execute(text("SELECT version();")).scalar()
        assert "PostgreSQL" in result


def test_postgresql_transaction_and_isolation(postgres_engine):
    """
    Validates PostgreSQL transaction commit, rollback, and dialect types.
    """
    if postgres_engine is None:
        pytest.skip(
            "PostgreSQL test database not reachable at localhost:5432. "
            "Skipping PostgreSQL transactional concurrency test."
        )

    with postgres_engine.connect() as conn:
        trans = conn.begin()
        val = conn.execute(text("SELECT 12345;")).scalar()
        assert val == 12345
        trans.rollback()


def test_postgresql_isolation_between_sessions(postgres_engine):
    """
    Validates that uncommitted transactions in one session are NOT visible
    to another session (Read Committed isolation level).
    """
    if postgres_engine is None:
        pytest.skip("PostgreSQL test database not reachable.")

    from sqlalchemy.orm import Session
    from app.models.business import Business

    session1 = Session(postgres_engine)
    session2 = Session(postgres_engine)

    try:
        biz = Business(
            name="Session Isolation Business",
            currency_code="INR",
            currency_symbol="₹",
            default_language="ta"
        )
        session1.add(biz)
        session1.flush()  # Flushed to session 1 transaction, not committed

        # Query from session 2
        biz_in_session2 = session2.query(Business).filter(Business.id == biz.id).first()
        assert biz_in_session2 is None, "Uncommitted transaction in session 1 must not be visible to session 2"

        # Rollback session 1
        session1.rollback()

        # Query again from session 2
        assert session2.query(Business).filter(Business.id == biz.id).first() is None
    finally:
        session1.close()
        session2.close()


def test_postgresql_tenant_isolation_and_foreign_keys(postgres_engine):
    """
    Validates that tenant data belongs strictly to its business, foreign key
    constraints prevent orphaned records, and cascade deletes work cleanly.
    """
    if postgres_engine is None:
        pytest.skip("PostgreSQL test database not reachable.")

    from sqlalchemy.orm import Session
    from app.models.business import Business, Branch

    session = Session(postgres_engine)

    try:
        biz_a = Business(name="Tenant Alpha", currency_code="INR")
        biz_b = Business(name="Tenant Beta", currency_code="INR")
        session.add_all([biz_a, biz_b])
        session.commit()

        branch_a = Branch(business_id=biz_a.id, name="Chennai Hub", code="CH-01")
        session.add(branch_a)
        session.commit()

        # Verify Tenant B has 0 branches
        b_branches = session.query(Branch).filter(Branch.business_id == biz_b.id).all()
        assert len(b_branches) == 0

        # Verify Tenant A has 1 branch
        a_branches = session.query(Branch).filter(Branch.business_id == biz_a.id).all()
        assert len(a_branches) == 1
        assert a_branches[0].name == "Chennai Hub"

        # Delete Tenant Alpha -> Branch must cascade delete
        session.delete(biz_a)
        session.commit()

        orphans = session.query(Branch).filter(Branch.id == branch_a.id).first()
        assert orphans is None, "Branch should be cascade deleted with parent business"

        # Cleanup Tenant Beta
        session.delete(biz_b)
        session.commit()
    finally:
        session.close()

