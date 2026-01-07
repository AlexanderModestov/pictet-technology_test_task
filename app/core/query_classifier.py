"""Query classification to determine data source requirements"""

import logging
import json
from typing import Dict, Any, List
from enum import Enum

from app.core.llm_client import llm_client

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Types of queries"""
    STRUCTURED = "STRUCTURED"
    UNSTRUCTURED = "UNSTRUCTURED"
    HYBRID = "HYBRID"


CLASSIFICATION_PROMPT = """
Analyze the following user query and classify it into one of three categories:

1. STRUCTURED: Questions about specific stock data (prices, ratios, comparisons, company information)
   Examples:
   - "What is Tesla's P/E ratio?"
   - "List all tech stocks"
   - "Compare Apple and Microsoft stock prices"
   - "Which stocks have the highest dividend yield?"

2. UNSTRUCTURED: Questions about macroeconomic trends, strategies, market analysis, general financial concepts
   Examples:
   - "What are the current inflation trends?"
   - "How is the housing market performing?"
   - "What is the Fed's stance on interest rates?"
   - "Explain quantitative easing"

3. HYBRID: Questions that need both stock data AND macroeconomic context
   Examples:
   - "How might inflation affect Tesla stock?"
   - "Compare tech stocks to current macro trends"
   - "Which sectors perform well in high interest rate environments?"
   - "Should I invest in technology stocks given current economic conditions?"

Query: {user_query}

Respond with a JSON object in the following format:
{{
    "classification": "STRUCTURED|UNSTRUCTURED|HYBRID",
    "reasoning": "Brief explanation of why this classification was chosen",
    "entities": ["list", "of", "extracted", "entities"],
    "sql_hint": "If STRUCTURED or HYBRID, what data might be needed from the database"
}}
"""


class QueryClassifier:
    """Classifies user queries to determine required data sources"""

    def __init__(self, client=None):
        """
        Initialize query classifier

        Args:
            client: LLMClient instance
        """
        self.client = client or llm_client

    def classify_query(self, query: str) -> Dict[str, Any]:
        """
        Classify a user query

        Args:
            query: User's question

        Returns:
            Dictionary with classification results:
            {
                "query_type": QueryType,
                "reasoning": str,
                "entities": List[str],
                "sql_hint": str
            }
        """
        try:
            # Create prompt
            user_prompt = CLASSIFICATION_PROMPT.format(user_query=query)

            # Get classification from LLM
            response = self.client.generate_json_response(
                system_prompt="You are a query classification expert for a stock research assistant. Always respond with valid JSON.",
                user_prompt=user_prompt,
                temperature=0.0  # Deterministic classification
            )

            # Parse JSON response
            classification_data = json.loads(response)

            # Validate and normalize
            query_type_str = classification_data.get("classification", "UNSTRUCTURED")
            try:
                query_type = QueryType(query_type_str)
            except ValueError:
                logger.warning(f"Invalid query type: {query_type_str}, defaulting to UNSTRUCTURED")
                query_type = QueryType.UNSTRUCTURED

            result = {
                "query_type": query_type,
                "reasoning": classification_data.get("reasoning", ""),
                "entities": classification_data.get("entities", []),
                "sql_hint": classification_data.get("sql_hint", "")
            }

            logger.info(f"Query classified as {query_type.value}: {result['reasoning']}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse classification JSON: {e}")
            # Default to UNSTRUCTURED if parsing fails
            return {
                "query_type": QueryType.UNSTRUCTURED,
                "reasoning": "Failed to classify, defaulting to unstructured",
                "entities": [],
                "sql_hint": ""
            }
        except Exception as e:
            logger.error(f"Error classifying query: {e}")
            # Default to UNSTRUCTURED if classification fails
            return {
                "query_type": QueryType.UNSTRUCTURED,
                "reasoning": f"Error during classification: {str(e)}",
                "entities": [],
                "sql_hint": ""
            }

    def needs_structured_data(self, classification: Dict[str, Any]) -> bool:
        """
        Check if query needs structured data

        Args:
            classification: Classification result

        Returns:
            True if structured data is needed
        """
        query_type = classification["query_type"]
        return query_type in [QueryType.STRUCTURED, QueryType.HYBRID]

    def needs_unstructured_data(self, classification: Dict[str, Any]) -> bool:
        """
        Check if query needs unstructured data

        Args:
            classification: Classification result

        Returns:
            True if unstructured data is needed
        """
        query_type = classification["query_type"]
        return query_type in [QueryType.UNSTRUCTURED, QueryType.HYBRID]


# Global query classifier instance
query_classifier = QueryClassifier()
