"""Tests for API endpoints"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestAPI:
    """Test suite for API endpoints"""

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["status"] == "running"

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "vector_db" in data
        assert "sql_db" in data
        assert "llm_api" in data

    # Note: The following tests require full system setup with API keys
    # Uncomment when ready to test end-to-end functionality

    # def test_query_endpoint_structured(self):
    #     """Test query endpoint with structured query"""
    #     response = client.post(
    #         "/api/v1/query",
    #         json={
    #             "question": "What is Tesla's stock price?",
    #             "include_sources": True
    #         }
    #     )
    #     assert response.status_code == 200
    #     data = response.json()
    #     assert "answer" in data
    #     assert "query_type" in data
    #     assert data["query_type"] in ["STRUCTURED", "HYBRID"]

    # def test_query_endpoint_invalid_request(self):
    #     """Test query endpoint with invalid request"""
    #     response = client.post(
    #         "/api/v1/query",
    #         json={"question": ""}  # Empty question
    #     )
    #     assert response.status_code == 422  # Validation error

    # def test_list_documents_endpoint(self):
    #     """Test document listing endpoint"""
    #     response = client.get("/api/v1/documents")
    #     assert response.status_code == 200
    #     data = response.json()
    #     assert "documents" in data
    #     assert "total_count" in data
