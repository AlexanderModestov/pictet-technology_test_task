"""Vector store operations using ChromaDB"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.unstructured.embeddings import embedding_generator
from app.unstructured.pdf_parser import pdf_parser
from app.unstructured.chunker import text_chunker

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages document storage and retrieval using ChromaDB"""

    def __init__(
        self,
        persist_path: Optional[str] = None,
        collection_name: str = "stock_documents"
    ):
        """
        Initialize vector store

        Args:
            persist_path: Path to ChromaDB persistence directory
            collection_name: Name of the collection
        """
        self.persist_path = persist_path or settings.chroma_persist_path
        self.collection_name = collection_name

        # Ensure persistence directory exists
        Path(self.persist_path).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={
                "description": "Stock investment research documents",
                "embedding_model": settings.embedding_model
            }
        )

        logger.info(f"Vector store initialized with collection: {self.collection_name}")

    def add_document(
        self,
        pdf_path: str,
        doc_type: str = "document"
    ) -> Dict[str, Any]:
        """
        Add a PDF document to the vector store

        Args:
            pdf_path: Path to PDF file
            doc_type: Type/category of document

        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"Adding document to vector store: {pdf_path}")

        # Extract text from PDF
        pages = pdf_parser.extract_text_from_pdf(pdf_path)

        if not pages:
            logger.warning(f"No text extracted from {pdf_path}")
            return {
                "success": False,
                "error": "No text extracted from PDF",
                "chunks_added": 0
            }

        # Chunk the pages
        doc_filename = Path(pdf_path).name
        chunks = text_chunker.chunk_pages(pages, doc_filename, doc_type)

        if not chunks:
            logger.warning(f"No chunks created from {pdf_path}")
            return {
                "success": False,
                "error": "No chunks created from PDF",
                "chunks_added": 0
            }

        # Generate embeddings
        chunk_texts = [chunk["text"] for chunk in chunks]
        embeddings = embedding_generator.generate_embeddings_batch(chunk_texts)

        # Prepare data for ChromaDB
        ids = [f"{doc_filename}_{chunk['chunk_index']}" for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]

        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunk_texts,
            metadatas=metadatas
        )

        logger.info(f"Added {len(chunks)} chunks from {doc_filename}")

        return {
            "success": True,
            "document_id": doc_filename,
            "chunks_added": len(chunks),
            "pages_processed": len(pages)
        }

    def search(
        self,
        query: str,
        top_k: int = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents

        Args:
            query: Search query text
            top_k: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of relevant document chunks with metadata
        """
        top_k = top_k or settings.top_k_results

        # Generate query embedding
        query_embedding = embedding_generator.generate_embedding(query)

        # Search in collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata
        )

        # Format results
        formatted_results = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                result = {
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results else None
                }
                formatted_results.append(result)

        logger.info(f"Found {len(formatted_results)} results for query")
        return formatted_results

    def search_with_threshold(
        self,
        query: str,
        top_k: int = None,
        similarity_threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Search with similarity threshold filtering

        Args:
            query: Search query text
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score (lower distance is better)

        Returns:
            List of relevant document chunks above threshold
        """
        threshold = similarity_threshold or settings.similarity_threshold
        results = self.search(query, top_k)

        # Filter by threshold (ChromaDB returns distances, lower is better)
        # Convert distance to similarity: similarity = 1 / (1 + distance)
        filtered_results = []
        for result in results:
            if result["distance"] is not None:
                similarity = 1 / (1 + result["distance"])
                result["similarity"] = similarity
                if similarity >= threshold:
                    filtered_results.append(result)
            else:
                # If no distance, include it
                filtered_results.append(result)

        logger.info(f"Filtered to {len(filtered_results)} results above threshold {threshold}")
        return filtered_results

    def get_document_count(self) -> int:
        """
        Get total number of document chunks in store

        Returns:
            Number of chunks
        """
        return self.collection.count()

    def delete_document(self, doc_filename: str) -> int:
        """
        Delete all chunks from a specific document

        Args:
            doc_filename: Filename of document to delete

        Returns:
            Number of chunks deleted
        """
        # Get all IDs for this document
        results = self.collection.get(
            where={"doc_filename": doc_filename}
        )

        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            logger.info(f"Deleted {len(results['ids'])} chunks from {doc_filename}")
            return len(results["ids"])

        return 0

    def list_documents(self) -> List[Dict[str, Any]]:
        """
        List all documents in the vector store

        Returns:
            List of document information
        """
        # Get all documents
        all_results = self.collection.get()

        # Extract unique documents
        documents = {}
        for metadata in all_results["metadatas"]:
            doc_filename = metadata.get("doc_filename")
            if doc_filename and doc_filename not in documents:
                documents[doc_filename] = {
                    "filename": doc_filename,
                    "doc_type": metadata.get("doc_type", "unknown"),
                    "chunk_count": 0
                }
            if doc_filename:
                documents[doc_filename]["chunk_count"] += 1

        return list(documents.values())

    def health_check(self) -> bool:
        """
        Check if vector store is healthy

        Returns:
            True if healthy, False otherwise
        """
        try:
            self.collection.count()
            return True
        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            return False

    def reset(self):
        """Reset/clear the entire collection (use with caution!)"""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={
                "description": "Stock investment research documents",
                "embedding_model": settings.embedding_model
            }
        )
        logger.warning(f"Collection {self.collection_name} has been reset")


# Global vector store instance
vector_store = VectorStore()
