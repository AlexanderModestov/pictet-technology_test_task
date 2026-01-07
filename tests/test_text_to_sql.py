"""Tests for Text-to-SQL functionality"""

import pytest
from app.structured.text_to_sql import TextToSQLGenerator
from app.structured.database import DatabaseManager
from app.utils.helpers import validate_sql_query


class TestTextToSQL:
    """Test suite for Text-to-SQL generation"""

    def test_validate_sql_query_valid(self):
        """Test SQL query validation with valid queries"""
        valid_queries = [
            "SELECT * FROM stocks",
            "SELECT symbol, stock_price FROM stocks WHERE sector = 'Technology'",
            "SELECT AVG(pe_ratio) FROM stocks GROUP BY sector",
        ]

        for query in valid_queries:
            assert validate_sql_query(query), f"Query should be valid: {query}"

    def test_validate_sql_query_invalid(self):
        """Test SQL query validation with invalid queries"""
        invalid_queries = [
            "DROP TABLE stocks",
            "DELETE FROM stocks WHERE id = 1",
            "UPDATE stocks SET stock_price = 100",
            "INSERT INTO stocks VALUES (1, 'TEST')",
            "SELECT * FROM stocks; DROP TABLE stocks;",
        ]

        for query in invalid_queries:
            assert not validate_sql_query(query), f"Query should be invalid: {query}"

    def test_validate_sql_query_must_start_with_select(self):
        """Test that queries must start with SELECT"""
        assert not validate_sql_query("FROM stocks SELECT *")

    # Note: The following tests require an OpenAI API key
    # Uncomment and configure when ready to test with real API

    # def test_generate_sql_simple_query(self):
    #     """Test SQL generation for a simple query"""
    #     generator = TextToSQLGenerator()
    #     sql = generator.generate_sql("What is Tesla's stock price?")
    #     assert sql is not None
    #     assert "SELECT" in sql.upper()
    #     assert validate_sql_query(sql)

    # def test_generate_sql_complex_query(self):
    #     """Test SQL generation for a complex query"""
    #     generator = TextToSQLGenerator()
    #     sql = generator.generate_sql("What is the average P/E ratio by sector?")
    #     assert sql is not None
    #     assert "AVG" in sql.upper()
    #     assert "GROUP BY" in sql.upper()
    #     assert validate_sql_query(sql)
