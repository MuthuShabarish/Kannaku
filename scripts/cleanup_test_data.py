"""
Kanakku Test Data Cleanup Utility

Safely inspects and purges synthetic test records generated during automated
verification and testing, without affecting production data.
"""
import sys
import os
import argparse
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database import SessionLocal, engine
from app.models.user import User
from app.models.business import Business

TEST_PHONES = [
    "+919876500001",  # Karthik test store
    "+919876540001",  # Meenakshi browser subagent test store
    "+919876599999",  # Murugan postgresql verification store
]


def inspect_test_records():
    db_paths = [
        Path(__file__).parent.parent / "backend" / "kanakku_dev.db",
        Path(__file__).parent.parent / "kanakku_dev.db"
    ]
    for p in db_paths:
        if p.exists():
            import sqlite3
            conn = sqlite3.connect(p)
            c = conn.cursor()
            try:
                rows = c.execute("SELECT phone, full_name, role FROM users").fetchall()
                print(f"Database {p.name} ({p}): {len(rows)} user records found:")
                for r in rows:
                    print(f"  - {r[1]} ({r[0]}) [{r[2]}]")
            except Exception as e:
                print(f"Database {p.name}: {e}")
            finally:
                conn.close()


def purge_test_records(confirmed=False):
    if not confirmed:
        print("Dry run only. Pass --confirm to execute deletion.")
        return

    # 1. Clean from active database (PostgreSQL)
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.phone.in_(TEST_PHONES)).all()
        for u in users:
            biz = db.query(Business).filter(Business.id == u.business_id).first()
            if biz:
                print(f"Deleting test business from active DB: {biz.name} ({biz.id})")
                db.delete(biz)  # Cascades to users, branches, warehouses
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error purging active DB test records: {e}")
    finally:
        db.close()

    # 2. Clean from any auxiliary SQLite test databases
    db_paths = [
        Path(__file__).parent.parent / "backend" / "kanakku_dev.db",
        Path(__file__).parent.parent / "kanakku_dev.db"
    ]
    for p in db_paths:
        if p.exists():
            import sqlite3
            conn = sqlite3.connect(p)
            c = conn.cursor()
            try:
                c.execute("PRAGMA foreign_keys = ON")
                for phone in TEST_PHONES:
                    rows = c.execute("SELECT business_id FROM users WHERE phone = ?", (phone,)).fetchall()
                    for r in rows:
                        c.execute("DELETE FROM businesses WHERE id = ?", (r[0],))
                conn.commit()
                print(f"Cleaned synthetic test records from {p.name}")
            except Exception as e:
                print(f"Error cleaning {p.name}: {e}")
            finally:
                conn.close()

    print("Purge completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up synthetic test records")
    parser.add_argument("--confirm", action="store_true", help="Confirm deletion")
    args = parser.parse_args()

    inspect_test_records()
    if args.confirm:
        purge_test_records(confirmed=True)
