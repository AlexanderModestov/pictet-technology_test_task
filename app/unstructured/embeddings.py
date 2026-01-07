"""Embedding generation for text chunks"""

import logging
from typing import List
from openai import OpenAI

from app.config import settings
from app.utils.helpers import retry_with_backoff

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates embeddings for text using OpenAI API"""

    def __init__(self, openai_client=None):
        """
        Initialize embedding generator

        Args:
            openai_client: OpenAI client instance
        """
        self.client = openai_client or OpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model

    @retry_with_backoff(
        max_retries=settings.llm_max_retries,
        initial_delay=settings.llm_retry_delay,
        exceptions=(Exception,)
    )
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding of dimension {len(embedding)}")
            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    @retry_with_backoff(
        max_retries=settings.llm_max_retries,
        initial_delay=settings.llm_retry_delay,
        exceptions=(Exception,)
    )
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a batch

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )

            embeddings = [item.embedding for item in response.data]
            logger.info(f"Generated {len(embeddings)} embeddings in batch")
            return embeddings

        except Exception as e:
            logger.error(f"Error generating embeddings batch: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings for this model

        Returns:
            Embedding dimension
        """
        # text-embedding-3-small has dimension 1536
        # text-embedding-3-large has dimension 3072
        if "text-embedding-3-small" in self.model:
            return 1536
        elif "text-embedding-3-large" in self.model:
            return 3072
        elif "text-embedding-ada-002" in self.model:
            return 1536
        else:
            # Default fallback
            logger.warning(f"Unknown embedding model {self.model}, assuming dimension 1536")
            return 1536


# Global embedding generator instance
embedding_generator = EmbeddingGenerator()
