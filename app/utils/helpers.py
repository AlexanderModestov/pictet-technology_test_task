"""Utility functions and helpers"""

import re
import time
import logging
from typing import Any, Callable, TypeVar
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


def clean_text(text: str) -> str:
    """
    Clean and normalize text by removing extra whitespace and special characters

    Args:
        text: Raw text to clean

    Returns:
        Cleaned text
    """
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters that might cause issues
    text = text.strip()
    return text


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Estimate token count for a given text

    Args:
        text: Text to count tokens for
        model: Model name for tokenization

    Returns:
        Estimated token count
    """
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"Failed to count tokens with tiktoken: {e}. Using approximation.")
        # Rough approximation: 1 token ≈ 4 characters
        return len(text) // 4


def truncate_text(text: str, max_tokens: int, model: str = "gpt-4") -> str:
    """
    Truncate text to fit within token limit

    Args:
        text: Text to truncate
        max_tokens: Maximum number of tokens
        model: Model name for tokenization

    Returns:
        Truncated text
    """
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
        tokens = encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        truncated_tokens = tokens[:max_tokens]
        return encoding.decode(truncated_tokens)
    except Exception as e:
        logger.warning(f"Failed to truncate with tiktoken: {e}. Using character approximation.")
        max_chars = max_tokens * 4
        return text[:max_chars]


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch

    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(f"Max retries ({max_retries}) reached for {func.__name__}")
                        raise

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    delay *= backoff_factor

            # This should never be reached, but for type checking
            raise last_exception if last_exception else Exception("Unexpected error in retry logic")

        return wrapper
    return decorator


def validate_sql_query(query: str) -> bool:
    """
    Validate SQL query for safety (prevent injection attacks)

    Args:
        query: SQL query to validate

    Returns:
        True if query is safe, False otherwise
    """
    query_upper = query.upper().strip()

    # Must start with SELECT
    if not query_upper.startswith("SELECT"):
        logger.warning("Query must start with SELECT")
        return False

    # Forbidden patterns
    forbidden_patterns = [
        r'\bDROP\b',
        r'\bDELETE\b',
        r'\bUPDATE\b',
        r'\bINSERT\b',
        r'\bALTER\b',
        r'\bCREATE\b',
        r'\bTRUNCATE\b',
        r'--',  # SQL comments
        r';.*;',  # Multiple statements
    ]

    for pattern in forbidden_patterns:
        if re.search(pattern, query_upper):
            logger.warning(f"Query contains forbidden pattern: {pattern}")
            return False

    return True


def format_currency(amount: float) -> str:
    """
    Format number as currency (USD)

    Args:
        amount: Amount to format

    Returns:
        Formatted currency string
    """
    return f"${amount:,.2f}"


def format_percentage(value: float) -> str:
    """
    Format number as percentage

    Args:
        value: Value to format (e.g., 0.15 for 15%)

    Returns:
        Formatted percentage string
    """
    return f"{value:.2f}%"


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert value to int

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Int value or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
