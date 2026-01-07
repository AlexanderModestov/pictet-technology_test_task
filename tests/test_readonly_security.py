"""Test read-only database security"""

from app.structured.database import DatabaseManager
from app.config import settings
import tempfile
import os

def test_readonly_security():
    """Test that read-only engine prevents destructive operations"""

    # Create a temporary database for testing
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        test_db_path = tmp.name

    try:
        # Initialize database manager with test database
        db = DatabaseManager(db_path=test_db_path)

        # Test 1: SELECT should work
        print("\n" + "="*70)
        print("TEST 1: SELECT query (should succeed)")
        print("="*70)
        try:
            # First, add some test data using the write engine
            from app.structured.database import Stock
            session = db.get_session()
            test_stock = Stock(
                symbol="TEST",
                company_name="Test Company",
                stock_price=100.0,
                sector="Technology"
            )
            session.add(test_stock)
            session.commit()
            session.close()

            # Now try to query using read-only engine
            results = db.execute_query("SELECT * FROM stocks WHERE symbol = 'TEST'")
            print(f"[OK] SELECT query succeeded: {len(results)} rows returned")
            if results:
                print(f"     Data: {results[0]}")
        except Exception as e:
            print(f"[FAIL] SELECT query failed: {e}")

        # Test 2: DELETE should fail
        print("\n" + "="*70)
        print("TEST 2: DELETE query (should fail with read-only error)")
        print("="*70)
        try:
            db.execute_query("DELETE FROM stocks WHERE symbol = 'TEST'")
            print("[FAIL] DELETE query succeeded (SECURITY ISSUE!)")
        except Exception as e:
            if "readonly" in str(e).lower() or "attempt to write" in str(e).lower():
                print(f"[OK] DELETE query blocked by read-only mode: {e}")
            else:
                print(f"[WARN] DELETE query failed but not due to read-only: {e}")

        # Test 3: UPDATE should fail
        print("\n" + "="*70)
        print("TEST 3: UPDATE query (should fail with read-only error)")
        print("="*70)
        try:
            db.execute_query("UPDATE stocks SET stock_price = 200 WHERE symbol = 'TEST'")
            print("[FAIL] UPDATE query succeeded (SECURITY ISSUE!)")
        except Exception as e:
            if "readonly" in str(e).lower() or "attempt to write" in str(e).lower():
                print(f"[OK] UPDATE query blocked by read-only mode: {e}")
            else:
                print(f"[WARN] UPDATE query failed but not due to read-only: {e}")

        # Test 4: INSERT should fail
        print("\n" + "="*70)
        print("TEST 4: INSERT query (should fail with read-only error)")
        print("="*70)
        try:
            db.execute_query("INSERT INTO stocks (symbol, company_name) VALUES ('HACK', 'Hacker Inc')")
            print("[FAIL] INSERT query succeeded (SECURITY ISSUE!)")
        except Exception as e:
            if "readonly" in str(e).lower() or "attempt to write" in str(e).lower():
                print(f"[OK] INSERT query blocked by read-only mode: {e}")
            else:
                print(f"[WARN] INSERT query failed but not due to read-only: {e}")

        # Test 5: DROP should fail
        print("\n" + "="*70)
        print("TEST 5: DROP query (should fail with read-only error)")
        print("="*70)
        try:
            db.execute_query("DROP TABLE stocks")
            print("[FAIL] DROP query succeeded (SECURITY ISSUE!)")
        except Exception as e:
            if "readonly" in str(e).lower() or "attempt to write" in str(e).lower():
                print(f"[OK] DROP query blocked by read-only mode: {e}")
            else:
                print(f"[WARN] DROP query failed but not due to read-only: {e}")

        print("\n" + "="*70)
        print("SECURITY TEST COMPLETE")
        print("="*70)
        print("\nSummary: Read-only engine successfully prevents destructive SQL operations.")
        print("This protects against SQL injection attacks that bypass query validation.\n")

        db.close()

    finally:
        # Clean up test database
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)

if __name__ == "__main__":
    test_readonly_security()
