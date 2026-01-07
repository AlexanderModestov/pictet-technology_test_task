"""Tests for RAG pipeline functionality"""

import pytest
from app.unstructured.chunker import TextChunker
from app.utils.helpers import count_tokens


class TestRAGPipeline:
    """Test suite for RAG pipeline components"""

    def test_text_chunker_basic(self):
        """Test basic text chunking"""
        chunker = TextChunker(chunk_size=100, chunk_overlap=10)
        text = "This is a test. " * 50  # Create long text

        chunks = chunker.chunk_text(text)
        assert len(chunks) > 0
        assert all("text" in chunk for chunk in chunks)
        assert all("chunk_index" in chunk for chunk in chunks)

    def test_text_chunker_respects_size(self):
        """Test that chunks respect size limits"""
        chunker = TextChunker(chunk_size=100, chunk_overlap=0)
        text = "Word " * 200

        chunks = chunker.chunk_text(text)
        for chunk in chunks:
            token_count = count_tokens(chunk["text"])
            assert token_count <= 120, f"Chunk too large: {token_count} tokens"

    def test_text_chunker_empty_text(self):
        """Test chunker with empty text"""
        chunker = TextChunker()
        chunks = chunker.chunk_text("")
        assert len(chunks) == 0

    def test_text_chunker_metadata(self):
        """Test that metadata is preserved"""
        chunker = TextChunker()
        text = "Test text " * 100
        metadata = {"doc_filename": "test.pdf", "page_number": 1}

        chunks = chunker.chunk_text(text, metadata)
        for chunk in chunks:
            assert "metadata" in chunk
            assert chunk["metadata"]["doc_filename"] == "test.pdf"
            assert chunk["metadata"]["page_number"] == 1

    # Note: The following tests require an OpenAI API key and ChromaDB
    # Uncomment and configure when ready to test with real services

    # def test_embedding_generation(self):
    #     """Test embedding generation"""
    #     from app.unstructured.embeddings import EmbeddingGenerator
    #     generator = EmbeddingGenerator()
    #     embedding = generator.generate_embedding("Test text")
    #     assert len(embedding) == 1536  # text-embedding-3-small dimension

    # def test_vector_store_add_search(self):
    #     """Test adding documents to vector store and searching"""
    #     from app.unstructured.vector_store import VectorStore
    #     store = VectorStore()
    #     # Add test document
    #     # Search and verify results
    #     pass
