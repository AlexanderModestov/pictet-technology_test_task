"""Text chunking strategies for document processing"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from app.config import settings
from app.utils.helpers import count_tokens

logger = logging.getLogger(__name__)


class TextChunker:
    """Handles text chunking with various strategies"""

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        min_chunk_size: int = 100
    ):
        """
        Initialize text chunker

        Args:
            chunk_size: Maximum chunk size in tokens
            chunk_overlap: Overlap between chunks in tokens
            min_chunk_size: Minimum viable chunk size in tokens
        """
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.min_chunk_size = min_chunk_size

        # Separators for recursive splitting (in order of preference)
        self.separators = [
            "\n\n",  # Paragraph breaks
            "\n",    # Line breaks
            ". ",    # Sentences
            " ",     # Words (fallback)
        ]

    def chunk_text(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Chunk text using recursive character splitting

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of chunk dictionaries with text and metadata
        """
        if not text or not text.strip():
            return []

        metadata = metadata or {}

        # Split text into chunks
        chunks = self._recursive_split(text)

        # Create chunk objects with metadata
        chunk_objects = []
        for idx, chunk_text in enumerate(chunks):
            chunk_obj = {
                "text": chunk_text,
                "chunk_index": idx,
                "chunk_size": count_tokens(chunk_text),
                "metadata": {
                    **metadata,
                    "created_at": datetime.utcnow().isoformat()
                }
            }
            chunk_objects.append(chunk_obj)

        logger.info(f"Created {len(chunk_objects)} chunks from text")
        return chunk_objects

    def _recursive_split(self, text: str, separator_index: int = 0) -> List[str]:
        """
        Recursively split text using separators

        Args:
            text: Text to split
            separator_index: Current separator index to try

        Returns:
            List of text chunks
        """
        # If text is small enough, return as is
        if count_tokens(text) <= self.chunk_size:
            if count_tokens(text) >= self.min_chunk_size:
                return [text]
            else:
                return []  # Too small, discard

        # Try current separator
        if separator_index >= len(self.separators):
            # No more separators, force split by characters
            return self._split_by_tokens(text)

        separator = self.separators[separator_index]
        splits = text.split(separator)

        # Merge splits into chunks
        chunks = []
        current_chunk = []
        current_size = 0

        for split in splits:
            split_with_sep = split + separator if separator != " " else split + " "
            split_tokens = count_tokens(split_with_sep)

            if current_size + split_tokens <= self.chunk_size:
                # Add to current chunk
                current_chunk.append(split)
                current_size += split_tokens
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunk_text = separator.join(current_chunk)
                    if count_tokens(chunk_text) >= self.min_chunk_size:
                        chunks.append(chunk_text)

                # If this split itself is too large, recursively split it
                if split_tokens > self.chunk_size:
                    sub_chunks = self._recursive_split(split, separator_index + 1)
                    chunks.extend(sub_chunks)
                    current_chunk = []
                    current_size = 0
                else:
                    current_chunk = [split]
                    current_size = split_tokens

        # Add remaining chunk
        if current_chunk:
            chunk_text = separator.join(current_chunk)
            if count_tokens(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)

        # Apply overlap if specified
        if self.chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._apply_overlap(chunks)

        return chunks

    def _split_by_tokens(self, text: str) -> List[str]:
        """
        Force split text by token count (fallback method)

        Args:
            text: Text to split

        Returns:
            List of text chunks
        """
        # Approximate character count per token
        chars_per_token = 4
        chunk_chars = self.chunk_size * chars_per_token

        chunks = []
        for i in range(0, len(text), chunk_chars):
            chunk = text[i:i + chunk_chars]
            if count_tokens(chunk) >= self.min_chunk_size:
                chunks.append(chunk)

        return chunks

    def _apply_overlap(self, chunks: List[str]) -> List[str]:
        """
        Apply overlap between chunks

        Args:
            chunks: List of text chunks

        Returns:
            List of chunks with overlap applied
        """
        if len(chunks) <= 1:
            return chunks

        overlapped_chunks = [chunks[0]]

        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]

            # Get overlap text from previous chunk
            overlap_text = self._get_overlap_text(prev_chunk, self.chunk_overlap)

            # Prepend overlap to current chunk
            overlapped_chunk = overlap_text + " " + current_chunk
            overlapped_chunks.append(overlapped_chunk)

        return overlapped_chunks

    def _get_overlap_text(self, text: str, overlap_tokens: int) -> str:
        """
        Get last N tokens worth of text

        Args:
            text: Source text
            overlap_tokens: Number of tokens to extract

        Returns:
            Overlap text
        """
        # Simple approximation: extract last N words
        words = text.split()
        overlap_words = words[-overlap_tokens:] if len(words) > overlap_tokens else words
        return " ".join(overlap_words)

    def chunk_pages(
        self,
        pages: List[Dict[str, Any]],
        doc_filename: str,
        doc_type: str = "document"
    ) -> List[Dict[str, Any]]:
        """
        Chunk multiple pages from a document

        Args:
            pages: List of page dictionaries with 'text' and 'page_number'
            doc_filename: Source document filename
            doc_type: Type of document

        Returns:
            List of chunk dictionaries
        """
        all_chunks = []
        total_chunks = 0

        # First pass: count total chunks
        for page in pages:
            page_chunks = self.chunk_text(page["text"])
            total_chunks += len(page_chunks)

        # Second pass: create chunks with complete metadata
        chunk_counter = 0
        for page in pages:
            page_text = page["text"]
            page_number = page["page_number"]

            metadata = {
                "doc_filename": doc_filename,
                "page_number": page_number,
                "doc_type": doc_type,
                "total_chunks": total_chunks
            }

            page_chunks = self.chunk_text(page_text, metadata)

            # Update chunk indices to be document-wide
            for chunk in page_chunks:
                chunk["chunk_index"] = chunk_counter
                chunk_counter += 1

            all_chunks.extend(page_chunks)

        logger.info(f"Created {len(all_chunks)} chunks from {len(pages)} pages")
        return all_chunks


# Global text chunker instance
text_chunker = TextChunker()
