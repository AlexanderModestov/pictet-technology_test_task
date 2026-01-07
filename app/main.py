"""FastAPI application entry point"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting Stock Investment Research Assistant API")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"LLM model: {settings.llm_model}")
    logger.info(f"Embedding model: {settings.embedding_model}")

    # Initialize databases (already done in module imports)
    from app.structured.database import db_manager
    from app.unstructured.vector_store import vector_store

    logger.info(f"SQL Database: {db_manager.health_check()}")
    logger.info(f"Vector Store: {vector_store.health_check()}")
    logger.info(f"Documents in vector store: {vector_store.get_document_count()}")

    yield

    # Shutdown
    logger.info("Shutting down Stock Investment Research Assistant API")
    db_manager.close()


# Create FastAPI application
app = FastAPI(
    title="Stock Investment Research Assistant",
    description="""
    A GenAI-powered assistant that combines structured stock data and unstructured
    macroeconomic documents to answer investment research questions.

    ## Features

    * **Text-to-SQL**: Query stock data using natural language
    * **RAG Pipeline**: Retrieve relevant information from PDF documents
    * **Hybrid Queries**: Combine both data sources for comprehensive answers
    * **Source Attribution**: Track where information comes from

    ## Data Sources

    * **Structured**: Stock prices, ratios, company information (SQL database)
    * **Unstructured**: Macroeconomic reports, market analysis (Vector database)
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint - API information
    """
    return {
        "name": "Stock Investment Research Assistant API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
