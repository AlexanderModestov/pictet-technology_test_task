"""Comprehensive pipeline test for Stock Investment Research Assistant"""

import requests
import json
from datetime import datetime
from typing import Dict, Any

API_BASE_URL = "http://localhost:8000"

class Colors:
    """ANSI color codes for terminal output (disabled for Windows compatibility)"""
    HEADER = ''
    OKBLUE = ''
    OKCYAN = ''
    OKGREEN = ''
    WARNING = ''
    FAIL = ''
    ENDC = ''
    BOLD = ''

def print_header(text: str):
    """Print a section header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}[OK] {text}{Colors.ENDC}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.FAIL}[ERROR] {text}{Colors.ENDC}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.OKCYAN}[INFO] {text}{Colors.ENDC}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.WARNING}[WARN] {text}{Colors.ENDC}")

def test_health_check() -> bool:
    """Test API health endpoint"""
    print_header("1. Health Check")
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/health", timeout=5)
        response.raise_for_status()
        data = response.json()

        print_info(f"Status: {data.get('status')}")
        print_info(f"Vector DB: {data.get('vector_db')}")
        print_info(f"SQL DB: {data.get('sql_db')}")
        print_info(f"LLM API: {data.get('llm_api')}")

        if data.get('status') == 'healthy':
            print_success("Health check passed")
            return True
        else:
            print_error("API is not healthy")
            return False
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False

def test_list_documents() -> bool:
    """Test document listing endpoint"""
    print_header("2. Document Inventory")
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/documents", timeout=10)
        response.raise_for_status()
        data = response.json()

        print_info(f"Total documents: {data.get('total_count', 0)}")

        if 'documents' in data:
            print(f"\n{Colors.BOLD}Documents loaded:{Colors.ENDC}")
            for i, doc in enumerate(data['documents'], 1):
                filename = doc.get('filename', 'Unknown')
                chunks = doc.get('chunk_count', 0)
                doc_type = doc.get('doc_type', 'N/A')
                print(f"  {i}. {filename}")
                print(f"     Chunks: {chunks}, Type: {doc_type}")

        print_success(f"Found {data.get('total_count', 0)} documents")
        return True
    except Exception as e:
        print_error(f"Document listing failed: {e}")
        return False

def test_query(question: str, expected_type: str = None, description: str = None) -> Dict[str, Any]:
    """Test a query and return results"""
    if description:
        print(f"\n{Colors.BOLD}Test: {description}{Colors.ENDC}")
    print(f"Question: \"{question}\"")

    try:
        payload = {
            "question": question,
            "include_sources": True
        }

        response = requests.post(
            f"{API_BASE_URL}/api/v1/query",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        response.raise_for_status()
        data = response.json()

        query_type = data.get('query_type', 'UNKNOWN')
        processing_time = data.get('processing_time_ms', 0)
        answer = data.get('answer', '')
        sources = data.get('sources', [])

        # Print results
        print_info(f"Query Type: {query_type}")
        print_info(f"Processing Time: {processing_time}ms ({processing_time/1000:.2f}s)")
        print_info(f"Sources: {len(sources)}")

        # Validate expected type
        if expected_type and query_type != expected_type:
            print_warning(f"Expected {expected_type}, got {query_type}")

        # Print sources
        if sources:
            print(f"\n{Colors.BOLD}Sources:{Colors.ENDC}")
            for i, source in enumerate(sources, 1):
                source_type = source.get('type', 'unknown')
                if source_type == 'structured':
                    print(f"  {i}. SQL Query: {source.get('query', 'N/A')[:100]}...")
                    print(f"     Results: {source.get('result_count', 0)} rows")
                elif source_type == 'unstructured':
                    print(f"  {i}. Documents: {source.get('chunk_count', 0)} chunks")

        # Print answer preview
        print(f"\n{Colors.BOLD}Answer Preview:{Colors.ENDC}")
        answer_preview = answer[:300] + "..." if len(answer) > 300 else answer
        print(f"{answer_preview}\n")

        # Check if answer is meaningful
        if "don't have enough information" in answer.lower():
            print_warning("Query returned insufficient data response")
            return {"success": False, "data": data}
        else:
            print_success("Query returned meaningful answer")
            return {"success": True, "data": data}

    except requests.exceptions.Timeout:
        print_error("Query timed out after 60 seconds")
        return {"success": False, "error": "timeout"}
    except Exception as e:
        print_error(f"Query failed: {e}")
        return {"success": False, "error": str(e)}

def run_test_suite():
    """Run comprehensive test suite"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}")
    print("="*80)
    print("    Stock Investment Research Assistant - Pipeline Test Suite    ".center(80))
    print("="*80)
    print(f"{Colors.ENDC}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "warnings": 0
    }

    # Test 1: Health Check
    if test_health_check():
        results["passed"] += 1
    else:
        results["failed"] += 1
        print_error("Cannot continue - API is not healthy")
        return
    results["total"] += 1

    # Test 2: Document Listing
    if test_list_documents():
        results["passed"] += 1
    else:
        results["failed"] += 1
    results["total"] += 1

    # Test 3: STRUCTURED Queries (SQL Database)
    print_header("3. STRUCTURED Queries (SQL Database)")

    structured_queries = [
        {
            "question": "What is the current price of Tesla?",
            "expected_type": "STRUCTURED",
            "description": "Single stock price lookup"
        },
        {
            "question": "Show me all technology stocks with PE ratio below 30",
            "expected_type": "STRUCTURED",
            "description": "Filtered sector query"
        },
        {
            "question": "What are the top 5 stocks by market cap?",
            "expected_type": "STRUCTURED",
            "description": "Aggregation and sorting"
        },
        {
            "question": "What is the average dividend yield in the healthcare sector?",
            "expected_type": "STRUCTURED",
            "description": "Sector aggregation"
        }
    ]

    for query_test in structured_queries:
        result = test_query(**query_test)
        results["total"] += 1
        if result.get("success"):
            results["passed"] += 1
        else:
            results["failed"] += 1

    # Test 4: UNSTRUCTURED Queries (Vector Database)
    print_header("4. UNSTRUCTURED Queries (Vector Database)")

    unstructured_queries = [
        {
            "question": "What are the key macroeconomic trends for 2025?",
            "expected_type": "UNSTRUCTURED",
            "description": "General economic outlook"
        },
        {
            "question": "What does the IMF say about global growth prospects?",
            "expected_type": "UNSTRUCTURED",
            "description": "Source-specific query"
        },
        {
            "question": "What are the inflation expectations?",
            "expected_type": "UNSTRUCTURED",
            "description": "Specific economic indicator"
        },
        {
            "question": "What are the risks to the global economy?",
            "expected_type": "UNSTRUCTURED",
            "description": "Risk assessment query"
        }
    ]

    for query_test in unstructured_queries:
        result = test_query(**query_test)
        results["total"] += 1
        if result.get("success"):
            results["passed"] += 1
        else:
            results["failed"] += 1

    # Test 5: HYBRID Queries (Both Databases)
    print_header("5. HYBRID Queries (SQL + Vector Search)")

    hybrid_queries = [
        {
            "question": "What is the target price of Tesla, and how does it compare to current macroeconomic trends?",
            "expected_type": "HYBRID",
            "description": "Tesla analysis with macro context"
        },
        {
            "question": "How do technology stock valuations look given the current interest rate environment?",
            "expected_type": "HYBRID",
            "description": "Sector valuation in macro context"
        },
        {
            "question": "Should I invest in high dividend stocks given the economic outlook?",
            "expected_type": "HYBRID",
            "description": "Investment recommendation query"
        }
    ]

    for query_test in hybrid_queries:
        result = test_query(**query_test)
        results["total"] += 1
        if result.get("success"):
            results["passed"] += 1
        else:
            results["failed"] += 1

    # Test 6: Edge Cases
    print_header("6. Edge Cases")

    edge_queries = [
        {
            "question": "What is the price of INVALID_TICKER?",
            "description": "Non-existent stock"
        },
        {
            "question": "Tell me about cryptocurrency regulations",
            "description": "Out of scope topic"
        },
        {
            "question": "What?",
            "description": "Vague question"
        }
    ]

    for query_test in edge_queries:
        result = test_query(**query_test)
        results["total"] += 1
        # Edge cases may fail - that's expected
        if result.get("success"):
            results["passed"] += 1
        else:
            results["warnings"] += 1

    # Print Summary
    print_header("Test Summary")

    print(f"{Colors.BOLD}Results:{Colors.ENDC}")
    print(f"  Total Tests: {results['total']}")
    print(f"  {Colors.OKGREEN}Passed: {results['passed']}{Colors.ENDC}")
    print(f"  {Colors.FAIL}Failed: {results['failed']}{Colors.ENDC}")
    print(f"  {Colors.WARNING}Warnings: {results['warnings']}{Colors.ENDC}")

    success_rate = (results['passed'] / results['total'] * 100) if results['total'] > 0 else 0
    print(f"\n{Colors.BOLD}Success Rate: {success_rate:.1f}%{Colors.ENDC}")

    if success_rate >= 80:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}[SUCCESS] Pipeline is working well!{Colors.ENDC}")
    elif success_rate >= 60:
        print(f"\n{Colors.WARNING}{Colors.BOLD}[WARN] Pipeline has some issues{Colors.ENDC}")
    else:
        print(f"\n{Colors.FAIL}{Colors.BOLD}[FAIL] Pipeline needs attention{Colors.ENDC}")

    print(f"\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

if __name__ == "__main__":
    try:
        run_test_suite()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Test interrupted by user{Colors.ENDC}\n")
    except Exception as e:
        print(f"\n\n{Colors.FAIL}Test suite failed: {e}{Colors.ENDC}\n")
