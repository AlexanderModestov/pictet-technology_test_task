"""Text-to-SQL conversion using LLM"""

import logging
from typing import Dict, List, Any, Optional
from openai import OpenAI

from app.config import settings
from app.structured.database import db_manager
from app.utils.helpers import validate_sql_query, retry_with_backoff

logger = logging.getLogger(__name__)


SQL_SCHEMA_CONTEXT = """
You are a SQL expert. Generate SQLite-compatible queries for the following schema:

TABLE: stocks
COLUMNS:
- symbol (VARCHAR): Stock ticker symbol (e.g., 'AAPL', 'TSLA US', 'MSFT'). Note: symbols may have exchange suffixes.
- company_name (VARCHAR): Full company name
- isin (VARCHAR): International Securities ID
- sector (VARCHAR): Industry sector (e.g., 'Technology', 'Healthcare')
- stock_price (DECIMAL): Current stock price in USD
- target_price (DECIMAL): Analyst target price in USD
- dividend_yield (DECIMAL): Annual dividend yield as percentage
- pe_ratio (DECIMAL): Price-to-Earnings ratio
- market_cap (BIGINT): Market capitalization in USD

IMPORTANT RULES:
1. For stock symbols: ALWAYS use "UPPER(symbol) LIKE 'TICKER%'" (not =) because symbols may have exchange suffixes
   Example: For Tesla, use "UPPER(symbol) LIKE 'TSLA%'" to match both 'TSLA' and 'TSLA US'
2. Use LIKE with % for partial text matching on company names and other text fields
3. Column names are case-sensitive
4. String comparisons should be case-insensitive (use UPPER() or LOWER())
5. Always limit results to 100 unless counting or the user specifically asks for more
6. Use appropriate aggregations (AVG, SUM, COUNT, MAX, MIN)
7. Return only SELECT statements
"""

SQL_GENERATION_PROMPT = """
{schema_context}

User Question: {user_question}

Generate ONLY the SQL query, no explanations or markdown formatting.
If the question cannot be answered with this schema, respond with: CANNOT_ANSWER

SQL Query:
"""


class TextToSQLGenerator:
    """Converts natural language questions to SQL queries"""

    def __init__(self, database_manager=None, openai_client=None):
        """
        Initialize Text-to-SQL generator

        Args:
            database_manager: DatabaseManager instance
            openai_client: OpenAI client instance
        """
        self.db_manager = database_manager or db_manager
        self.client = openai_client or OpenAI(api_key=settings.openai_api_key)

    @retry_with_backoff(
        max_retries=settings.llm_max_retries,
        initial_delay=settings.llm_retry_delay,
        exceptions=(Exception,)
    )
    def generate_sql(self, question: str) -> Optional[str]:
        """
        Generate SQL query from natural language question

        Args:
            question: User's question in natural language

        Returns:
            SQL query string or None if cannot be answered
        """
        try:
            # Get schema context
            schema_context = SQL_SCHEMA_CONTEXT

            # Create prompt
            prompt = SQL_GENERATION_PROMPT.format(
                schema_context=schema_context,
                user_question=question
            )

            # Call LLM
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "You are a SQL expert that generates safe, read-only SQL queries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,  # Deterministic output
                max_tokens=500
            )

            sql_query = response.choices[0].message.content.strip()

            # Clean up the response
            sql_query = self._clean_sql_response(sql_query)

            # Check if LLM couldn't answer
            if sql_query == "CANNOT_ANSWER":
                logger.info("LLM determined question cannot be answered with available schema")
                return None

            # Validate SQL for safety
            if not validate_sql_query(sql_query):
                logger.warning(f"Generated SQL failed validation: {sql_query}")
                return None

            logger.info(f"Generated SQL query: {sql_query}")
            return sql_query

        except Exception as e:
            logger.error(f"Error generating SQL: {e}")
            raise

    def _clean_sql_response(self, sql: str) -> str:
        """
        Clean SQL response from LLM

        Args:
            sql: Raw SQL from LLM

        Returns:
            Cleaned SQL query
        """
        # Remove markdown code blocks
        sql = sql.replace("```sql", "").replace("```", "")

        # Remove leading/trailing whitespace
        sql = sql.strip()

        # Remove any trailing semicolons
        sql = sql.rstrip(";")

        return sql

    def execute_text_to_sql(self, question: str) -> Dict[str, Any]:
        """
        Generate SQL from question and execute it

        Args:
            question: User's natural language question

        Returns:
            Dictionary with query results and metadata
        """
        try:
            # Generate SQL
            sql_query = self.generate_sql(question)

            if not sql_query:
                return {
                    "success": False,
                    "error": "Could not generate SQL query for this question",
                    "query": None,
                    "results": []
                }

            # Execute query
            results = self.db_manager.execute_query(sql_query)

            return {
                "success": True,
                "query": sql_query,
                "results": results,
                "count": len(results)
            }

        except Exception as e:
            logger.error(f"Error executing text-to-SQL: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": None,
                "results": []
            }

    def format_results_as_text(self, results: List[Dict[str, Any]]) -> str:
        """
        Format SQL query results as human-readable text

        Args:
            results: List of result dictionaries

        Returns:
            Formatted text representation
        """
        if not results:
            return "No results found."

        if len(results) == 1 and len(results[0]) == 1:
            # Single value result
            key = list(results[0].keys())[0]
            value = results[0][key]
            return f"{key}: {value}"

        # Multiple results - format as a simple table
        lines = []
        if results:
            # Header
            headers = list(results[0].keys())
            lines.append(" | ".join(headers))
            lines.append("-" * (sum(len(h) for h in headers) + 3 * len(headers)))

            # Rows
            for row in results[:10]:  # Limit to first 10 rows for readability
                values = [str(row.get(h, "")) for h in headers]
                lines.append(" | ".join(values))

            if len(results) > 10:
                lines.append(f"... and {len(results) - 10} more rows")

        return "\n".join(lines)


# Global text-to-SQL generator instance
text_to_sql_generator = TextToSQLGenerator()
