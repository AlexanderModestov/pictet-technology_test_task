"""API route definitions"""

import logging
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, status

from app.api.schemas import (
    QueryRequest,
    QueryResponse,
    DocumentUploadResponse,
    StockUploadResponse,
    HealthCheckResponse,
    ListDocumentsResponse,
    DeleteDocumentResponse,
    DocumentInfo
)
from app.core.response_generator import response_generator
from app.unstructured.vector_store import vector_store
from app.structured.csv_ingester import csv_ingester
from app.structured.database import db_manager

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["api"])


# Query Endpoint

@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Submit a question and receive an answer

    This endpoint:
    - Classifies the query type
    - Retrieves relevant data from SQL and/or vector databases
    - Generates a comprehensive response using LLM
    """
    try:
        response = response_generator.generate_response(
            question=request.question,
            include_sources=request.include_sources
        )
        return response
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )


# Document Management Endpoints

@router.post("/documents", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = "document"
):
    """
    Upload a PDF document for indexing

    The document will be:
    - Parsed for text content
    - Chunked into manageable segments
    - Embedded and stored in the vector database
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )

    try:
        # Save uploaded file temporarily
        temp_path = Path("data/pdfs") / file.filename
        temp_path.parent.mkdir(parents=True, exist_ok=True)

        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Add to vector store
        result = vector_store.add_document(str(temp_path), doc_type)

        if result["success"]:
            return DocumentUploadResponse(
                status="success",
                document_id=result["document_id"],
                chunks_created=result["chunks_added"],
                message="Document processed and indexed successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to process document")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading document: {str(e)}"
        )


@router.get("/documents", response_model=ListDocumentsResponse)
async def list_documents():
    """
    List all documents in the vector store
    """
    try:
        documents = vector_store.list_documents()
        return ListDocumentsResponse(
            documents=[DocumentInfo(**doc) for doc in documents],
            total_count=len(documents)
        )
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing documents: {str(e)}"
        )


@router.delete("/documents/{filename}", response_model=DeleteDocumentResponse)
async def delete_document(filename: str):
    """
    Delete a document from the vector store
    """
    try:
        chunks_deleted = vector_store.delete_document(filename)

        if chunks_deleted > 0:
            return DeleteDocumentResponse(
                status="success",
                chunks_deleted=chunks_deleted,
                message=f"Document '{filename}' deleted successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{filename}' not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting document: {str(e)}"
        )


# Stock Data Management Endpoints

@router.post("/stocks", response_model=StockUploadResponse)
async def upload_stocks(
    file: UploadFile = File(...),
    column_mapping: str = None
):
    """
    Upload/update stock data from CSV or Excel file

    The file should contain columns:
    - symbol (required)
    - company_name (required)
    - isin, sector, stock_price, target_price, dividend_yield, pe_ratio, market_cap (optional)

    Supported formats: .csv, .xlsx, .xls

    Args:
        file: CSV or Excel file with stock data
        column_mapping: Optional column mapping name ('equities' for standard format)
    """
    # Validate file type
    allowed_extensions = ('.csv', '.xlsx', '.xls')
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only CSV and Excel files are supported. Allowed: {', '.join(allowed_extensions)}"
        )

    try:
        # Save uploaded file temporarily
        temp_path = Path("data") / file.filename
        temp_path.parent.mkdir(parents=True, exist_ok=True)

        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Ingest CSV/Excel with optional column mapping
        stats = csv_ingester.ingest_csv(str(temp_path), column_mapping)

        return StockUploadResponse(
            status="success",
            records_processed=stats["processed"],
            records_updated=stats["updated"],
            records_inserted=stats["inserted"]
        )

    except Exception as e:
        logger.error(f"Error uploading stocks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading stocks: {str(e)}"
        )


# Health Check Endpoint

@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Check health status of all system components
    """
    try:
        # Check vector database
        vector_db_status = "connected" if vector_store.health_check() else "disconnected"

        # Check SQL database
        sql_db_status = "connected" if db_manager.health_check() else "disconnected"

        # Check LLM API (simple check - we assume it's available if configured)
        llm_api_status = "connected" if response_generator.client else "disconnected"

        # Overall status
        overall_status = "healthy" if all([
            vector_db_status == "connected",
            sql_db_status == "connected",
            llm_api_status == "connected"
        ]) else "unhealthy"

        return HealthCheckResponse(
            status=overall_status,
            vector_db=vector_db_status,
            sql_db=sql_db_status,
            llm_api=llm_api_status
        )

    except Exception as e:
        logger.error(f"Error during health check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )
