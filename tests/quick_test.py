"""Quick pipeline test - fast validation"""

import requests
import json

API_URL = "http://localhost:8000"

def test_query(question, description):
    """Test a single query"""
    print(f"\n{'='*70}")
    print(f"TEST: {description}")
    print(f"{'='*70}")
    print(f"Question: {question}\n")

    try:
        response = requests.post(
            f"{API_URL}/api/v1/query",
            json={"question": question, "include_sources": True},
            timeout=30
        )
        data = response.json()

        print(f"[{data['query_type']}] {data['processing_time_ms']}ms")
        print(f"Sources: {len(data.get('sources', []))}")

        # Print answer
        answer = data.get('answer', '')
        if len(answer) > 200:
            print(f"\nAnswer: {answer[:200]}...\n")
        else:
            print(f"\nAnswer: {answer}\n")

        # Check success
        if "don't have enough information" in answer.lower():
            print("[WARN] Insufficient data")
            return False
        else:
            print("[OK] Success")
            return True

    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def main():
    print("\n" + "="*70)
    print("  QUICK PIPELINE TEST".center(70))
    print("="*70)

    # Test health
    print("\n1. Health Check...")
    try:
        r = requests.get(f"{API_URL}/api/v1/health", timeout=5)
        health = r.json()
        print(f"   Status: {health['status']}")
        print(f"   Vector DB: {health['vector_db']}")
        print(f"   SQL DB: {health['sql_db']}")
    except Exception as e:
        print(f"   [ERROR] {e}")
        return

    # Test queries
    results = []

    # SQL query
    results.append(test_query(
        "What are the top 3 stocks by market cap?",
        "SQL Query - Top Stocks"
    ))

    # Vector query
    results.append(test_query(
        "What are the key economic trends?",
        "Vector Search - Economic Trends"
    ))

    # Hybrid query
    results.append(test_query(
        "How do current stock valuations compare to economic conditions?",
        "Hybrid Query - Stocks + Economics"
    ))

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY".center(70))
    print(f"{'='*70}")
    passed = sum(results)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")
    print(f"Success Rate: {(passed/total*100):.0f}%\n")

    if passed == total:
        print("[SUCCESS] All tests passed!\n")
    elif passed >= total/2:
        print("[WARN] Some tests failed\n")
    else:
        print("[FAIL] Multiple failures\n")

if __name__ == "__main__":
    main()
