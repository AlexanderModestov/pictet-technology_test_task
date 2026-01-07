"""Response generation orchestrator combining structured and unstructured data"""

import logging
import time
from typing import Dict, Any, List, Optional

from app.core.llm_client import llm_client
from app.core.query_classifier import query_classifier, QueryType
from app.structured.text_to_sql import text_to_sql_generator
from app.unstructured.vector_store import vector_store
from app.utils.helpers import truncate_text
from app.config import settings

logger = logging.getLogger(__name__)


RESPONSE_SYNTHESIS_PROMPT = """
You are a professional stock investment research assistant with expertise in both quantitative analysis and macroeconomic trends.

Generate a comprehensive, helpful answer based on the provided context below.

{structured_context}

{unstructured_context}

USER QUESTION:
{user_question}

INSTRUCTIONS:
1. Synthesize information from both structured data and document context when available
2. Be specific with numbers and data points - cite exact values
3. Acknowledge any limitations or missing data honestly
4. Keep your response concise but informative (2-4 paragraphs)
5. If sources provide conflicting information, note the discrepancy
6. Use professional, clear language suitable for investment research
7. Do not make up information - only use the provided context

Generate a professional, helpful response:
"""


class ResponseGenerator:
    """Orchestrates query processing and response generation"""

    def __init__(
        self,
        client=None,
        classifier=None,
        sql_generator=None,
        vector_db=None
    ):
        """
        Initialize response generator

        Args:
            client: LLMClient instance
            classifier: QueryClassifier instance
            sql_generator: TextToSQLGenerator instance
            vector_db: VectorStore instance
        """
        self.client = client or llm_client
        self.classifier = classifier or query_classifier
        self.sql_generator = sql_generator or text_to_sql_generator
        self.vector_db = vector_db or vector_store

    def generate_response(
        self,
        question: str,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive response to a user question

        Args:
            question: User's question
            include_sources: Whether to include source information

        Returns:
            Dictionary with answer, sources, and metadata
        """
        start_time = time.time()

        try:
            # Step 1: Classify the query
            classification = self.classifier.classify_query(question)
            query_type = classification["query_type"]

            logger.info(f"Processing {query_type.value} query: {question}")

            # Step 2: Retrieve data based on classification
            structured_data = None
            unstructured_data = None
            sources = []

            if self.classifier.needs_structured_data(classification):
                structured_data = self._get_structured_data(question)
                if structured_data and structured_data["success"]:
                    sources.append({
                        "type": "structured",
                        "query": structured_data["query"],
                        "result_count": structured_data["count"]
                    })

            if self.classifier.needs_unstructured_data(classification):
                unstructured_data = self._get_unstructured_data(question)
                if unstructured_data:
                    sources.append({
                        "type": "unstructured",
                        "chunk_count": len(unstructured_data)
                    })

            # Step 3: Generate response
            answer = self._synthesize_response(
                question=question,
                structured_data=structured_data,
                unstructured_data=unstructured_data
            )

            processing_time = int((time.time() - start_time) * 1000)

            response = {
                "answer": answer,
                "query_type": query_type.value,
                "processing_time_ms": processing_time
            }

            if include_sources:
                response["sources"] = sources

            logger.info(f"Response generated in {processing_time}ms")
            return response

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "answer": "I apologize, but I encountered an error processing your question. Please try rephrasing or contact support if the issue persists.",
                "query_type": "ERROR",
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "error": str(e)
            }

    def _get_structured_data(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve structured data from SQL database

        Args:
            question: User's question

        Returns:
            Structured query results or None
        """
        try:
            result = self.sql_generator.execute_text_to_sql(question)
            if result["success"] and result["results"]:
                logger.info(f"Retrieved {len(result['results'])} structured results")
                return result
            else:
                logger.info("No structured data found")
                return None
        except Exception as e:
            logger.error(f"Error retrieving structured data: {e}")
            return None

    def _get_unstructured_data(self, question: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve unstructured data from vector store

        Args:
            question: User's question

        Returns:
            List of relevant document chunks or None
        """
        try:
            results = self.vector_db.search_with_threshold(question)
            if results:
                logger.info(f"Retrieved {len(results)} document chunks")
                return results
            else:
                logger.info("No relevant documents found")
                return None
        except Exception as e:
            logger.error(f"Error retrieving unstructured data: {e}")
            return None

    def _synthesize_response(
        self,
        question: str,
        structured_data: Optional[Dict[str, Any]],
        unstructured_data: Optional[List[Dict[str, Any]]]
    ) -> str:
        """
        Synthesize final response from all data sources

        Args:
            question: User's question
            structured_data: SQL query results
            unstructured_data: Document chunks

        Returns:
            Synthesized answer
        """
        # Build context sections
        structured_context = self._format_structured_context(structured_data)
        unstructured_context = self._format_unstructured_context(unstructured_data)

        # If no data available, return appropriate message
        if not structured_context and not unstructured_context:
            return "I don't have enough information in my database to answer this question. Please ensure the relevant stock data and documents have been loaded."

        # Create prompt
        prompt = RESPONSE_SYNTHESIS_PROMPT.format(
            structured_context=structured_context,
            unstructured_context=unstructured_context,
            user_question=question
        )

        # Truncate if needed
        prompt = truncate_text(prompt, settings.max_context_tokens)

        # Generate response
        try:
            answer = self.client.generate_response(
                system_prompt="You are a professional stock investment research assistant.",
                user_prompt=prompt,
                temperature=0.7,
                max_tokens=1000
            )
            return answer
        except Exception as e:
            logger.error(f"Error synthesizing response: {e}")
            return "I encountered an error generating the response. Please try again."

    def _format_structured_context(self, data: Optional[Dict[str, Any]]) -> str:
        """Format structured data for LLM context"""
        if not data or not data.get("success") or not data.get("results"):
            return ""

        context = "STRUCTURED DATA FROM DATABASE:\n"
        context += f"SQL Query: {data['query']}\n\n"
        context += "Results:\n"

        results = data["results"]
        if len(results) == 1 and len(results[0]) <= 3:
            # Simple result, format inline
            for key, value in results[0].items():
                context += f"  {key}: {value}\n"
        else:
            # Table format
            for i, row in enumerate(results[:20], 1):  # Limit to 20 rows
                context += f"  Row {i}: {row}\n"
            if len(results) > 20:
                context += f"  ... and {len(results) - 20} more rows\n"

        return context

    def _format_unstructured_context(self, data: Optional[List[Dict[str, Any]]]) -> str:
        """Format unstructured data for LLM context"""
        if not data:
            return ""

        context = "\nDOCUMENT CONTEXT:\n"
        for i, chunk in enumerate(data, 1):
            doc_name = chunk["metadata"].get("doc_filename", "Unknown")
            page_num = chunk["metadata"].get("page_number", "?")
            similarity = chunk.get("similarity", 0)

            context += f"\n[Source {i}: {doc_name}, Page {page_num}, Relevance: {similarity:.2f}]\n"
            context += f"{chunk['text']}\n"

        return context


# Global response generator instance
response_generator = ResponseGenerator()
