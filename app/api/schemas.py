"""Pydantic schemas for API request/response validation"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# Query Endpoint Schemas

class QueryRequest(BaseModel):
    """Request schema for query endpoint"""
    question: str = Field(..., min_length=1, description="User's question")
    include_sources: bool = Field(default=True, description="Include source information in response")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is the target price of Tesla?",
                "include_sources": True
            }
        }


class SourceInfo(BaseModel):
    """Information about a data source used"""
    type: str = Field(..., description="Type of source (structured/unstructured)")
    query: Optional[str] = Field(None, description="SQL query for structured sources")
    result_count: Optional[int] = Field(None, description="Number of results")
    chunk_count: Optional[int] = Field(None, description="Number of document chunks")


class QueryResponse(BaseModel):
    """Response schema for query endpoint"""
    answer: str = Field(..., description="Generated answer")
    sources: Optional[List[SourceInfo]] = Field(None, description="Source information")
    query_type: str = Field(..., description="Type of query (STRUCTURED/UNSTRUCTURED/HYBRID)")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "The target price of Tesla (TSLA) is $250.00, which represents a 15% upside from the current stock price of $217.50.",
                "sources": [
                    {
                        "type": "structured",
                        "query": "SELECT symbol, target_price, stock_price FROM stocks WHERE symbol = 'TSLA'",
                        "result_count": 1
                    }
                ],
                "query_type": "STRUCTURED",
                "processing_time_ms": 245
            }
        }


# Document Upload Schemas

class DocumentUploadResponse(BaseModel):
    """Response schema for document upload"""
    status: str = Field(..., description="Status (success/error)")
    document_id: str = Field(..., description="Document identifier")
    chunks_created: int = Field(..., description="Number of chunks created")
    message: str = Field(..., description="Human-readable message")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "document_id": "macro_report_2024.pdf",
                "chunks_created": 45,
                "message": "Document processed and indexed successfully"
            }
        }


# Stock Data Upload Schemas

class StockUploadResponse(BaseModel):
    """Response schema for stock CSV upload"""
    status: str = Field(..., description="Status (success/error)")
    records_processed: int = Field(..., description="Total records processed")
    records_updated: int = Field(..., description="Records updated")
    records_inserted: int = Field(..., description="Records inserted")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "records_processed": 150,
                "records_updated": 12,
                "records_inserted": 138
            }
        }


# Health Check Schemas

class HealthCheckResponse(BaseModel):
    """Response schema for health check"""
    status: str = Field(..., description="Overall health status")
    vector_db: str = Field(..., description="Vector database status")
    sql_db: str = Field(..., description="SQL database status")
    llm_api: str = Field(..., description="LLM API status")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "vector_db": "connected",
                "sql_db": "connected",
                "llm_api": "connected"
            }
        }


# List Documents Schema

class DocumentInfo(BaseModel):
    """Information about a document in the vector store"""
    filename: str = Field(..., description="Document filename")
    doc_type: str = Field(..., description="Document type/category")
    chunk_count: int = Field(..., description="Number of chunks")


class ListDocumentsResponse(BaseModel):
    """Response schema for listing documents"""
    documents: List[DocumentInfo] = Field(..., description="List of documents")
    total_count: int = Field(..., description="Total number of documents")

    class Config:
        json_schema_extra = {
            "example": {
                "documents": [
                    {
                        "filename": "macro_report_2024.pdf",
                        "doc_type": "macro_report",
                        "chunk_count": 45
                    }
                ],
                "total_count": 1
            }
        }


# Delete Document Schema

class DeleteDocumentResponse(BaseModel):
    """Response schema for document deletion"""
    status: str = Field(..., description="Status (success/error)")
    chunks_deleted: int = Field(..., description="Number of chunks deleted")
    message: str = Field(..., description="Human-readable message")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "chunks_deleted": 45,
                "message": "Document deleted successfully"
            }
        }


# Error Response Schema

class ErrorResponse(BaseModel):
    """Schema for error responses"""
    detail: str = Field(..., description="Error message")
    error_type: Optional[str] = Field(None, description="Type of error")

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Invalid file format. Please upload a PDF file.",
                "error_type": "ValidationError"
            }
        }
