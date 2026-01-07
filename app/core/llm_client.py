"""LLM client wrapper for OpenAI API"""

import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI

from app.config import settings
from app.utils.helpers import retry_with_backoff

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper for OpenAI LLM API calls"""

    def __init__(self, openai_client=None):
        """
        Initialize LLM client

        Args:
            openai_client: OpenAI client instance
        """
        self.client = openai_client or OpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model

    @retry_with_backoff(
        max_retries=settings.llm_max_retries,
        initial_delay=settings.llm_retry_delay,
        exceptions=(Exception,)
    )
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate chat completion

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            response_format: Optional response format (e.g., {"type": "json_object"})

        Returns:
            Response text from LLM
        """
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            if response_format:
                kwargs["response_format"] = response_format

            response = self.client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content
            logger.debug(f"LLM response: {content[:100]}...")
            return content

        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            raise

    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate a response with system and user prompts

        Args:
            system_prompt: System-level instructions
            user_prompt: User query/prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Response text from LLM
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

    def generate_json_response(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0
    ) -> str:
        """
        Generate a JSON-formatted response

        Args:
            system_prompt: System-level instructions
            user_prompt: User query/prompt
            temperature: Sampling temperature

        Returns:
            JSON string response from LLM
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return self.chat_completion(
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"}
        )


# Global LLM client instance
llm_client = LLMClient()
