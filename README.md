# Stock Investment Research Assistant API

A GenAI-powered REST API that combines structured stock data with unstructured financial documents to answer investment research questions.

**Base URL:** `{SERVER_ADDRESS}/api/v1`
**Interactive Docs:** `{SERVER_ADDRESS}/docs`

> Replace `{SERVER_ADDRESS}` with your actual server address:
> - Local development: `http://localhost:8000`
> - Cloud deployment: `https://your-domain.com` or your cloud service URL

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Add your OPENAI_API_KEY to .env

# 3. Start server
python -m app.main
```

**Local development:** Server runs at `http://localhost:8000`

**Production:** Server runs at your configured domain or cloud service URL

---

## API Endpoints

### 1. Query Endpoint

Ask questions about stocks and financial documents.

**Endpoint:** `POST /api/v1/query`

**Request Body:**
```json
{
  "question": "What is Tesla's P/E ratio?",
  "include_sources": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| question | string | Yes | Investment research question |
| include_sources | boolean | No | Include source information (default: true) |

**Response:**
```json
{
  "answer": "Tesla (TSLA) has a P/E ratio of 52.3",
  "query_type": "STRUCTURED",
  "processing_time_ms": 245,
  "sources": [
    {
      "type": "structured",
      "query": "SELECT symbol, pe_ratio FROM stocks WHERE symbol = 'TSLA'",
      "result_count": 1
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| answer | string | Generated answer |
| query_type | string | STRUCTURED / UNSTRUCTURED / HYBRID |
| processing_time_ms | integer | Processing time in milliseconds |
| sources | array | Source information (optional) |

**Query Types:**

- **STRUCTURED** - Queries stock database (prices, ratios, sectors)
- **UNSTRUCTURED** - Searches PDF documents (market trends, analysis)
- **HYBRID** - Combines both sources

---

### 2. Upload Document

Upload and index PDF documents.

**Endpoint:** `POST /api/v1/documents`

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | file | Yes | PDF file |
| doc_type | string | No | Document category |

**Response:**
```json
{
  "status": "success",
  "document_id": "market_report_2024.pdf",
  "chunks_created": 45,
  "message": "Document processed and indexed successfully"
}
```

---

### 3. List Documents

Get all indexed documents.

**Endpoint:** `GET /api/v1/documents`

**Response:**
```json
{
  "documents": [
    {
      "filename": "market_report_2024.pdf",
      "doc_type": "market_analysis",
      "chunk_count": 45
    }
  ],
  "total_count": 1
}
```

---

### 4. Delete Document

Remove a document from the system.

**Endpoint:** `DELETE /api/v1/documents/{filename}`

**Response:**
```json
{
  "status": "success",
  "chunks_deleted": 45,
  "message": "Document deleted successfully"
}
```

---

### 5. Upload Stock Data

Upload or update stock data from CSV or Excel files.

**Endpoint:** `POST /api/v1/stocks`

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | file | Yes | CSV or Excel file (.csv, .xlsx, .xls) |
| column_mapping | string | No | Column mapping preset (e.g., "equities") |

**File Format Requirements:**

**Required columns:**
- `symbol` - Stock ticker (e.g., "AAPL")
- `company_name` - Company name (e.g., "Apple Inc.")

**Optional columns:**
- `isin`, `sector`, `stock_price`, `target_price`, `dividend_yield`, `pe_ratio`, `market_cap`

**Response:**
```json
{
  "status": "success",
  "records_processed": 150,
  "records_updated": 12,
  "records_inserted": 138
}
```

---

### 6. Health Check

Check system health status.

**Endpoint:** `GET /api/v1/health`

**Response:**
```json
{
  "status": "healthy",
  "vector_db": "connected",
  "sql_db": "connected",
  "llm_api": "connected"
}
```

---

## Sample Questions

**Structured Queries (Stock Data):**
- "What is Apple's stock price?"
- "Compare P/E ratios of Apple and Microsoft"
- "List all stocks in the Technology sector"
- "Which stock has the highest dividend yield?"

**Unstructured Queries (Documents):**
- "What are current inflation trends?"
- "How do rising interest rates affect tech stocks?"
- "What did the Fed announce in their recent meeting?"

**Hybrid Queries (Combined):**
- "Should I invest in Tesla given current market conditions?"
- "How might inflation affect Apple's stock?"
- "Which high-dividend stocks perform well during recessions?"

---

## Configuration

Create a `.env` file:

```ini
# Required
OPENAI_API_KEY=sk-your-api-key-here

---

## Docker Deployment

```bash
# Build
docker build -f deploy/Dockerfile -t stock-research-assistant .

# Run
docker run -d \
  -p 8080:8080 \
  -e OPENAI_API_KEY=your-api-key \
  -v $(pwd)/data:/app/data \
  --name stock-assistant \
  stock-research-assistant
```

**Local Docker:** Access at `http://localhost:8080`

**Cloud deployment:** Access at your configured domain or cloud service URL

See `deploy/DEPLOYMENT.md` for cloud deployment instructions.

---

## Error Responses

All errors return standard HTTP status codes with JSON error details:

```json
{
  "detail": "Error description"
}
```

**Common Status Codes:**
- `200` - Success
- `400` - Bad Request (invalid input)
- `404` - Not Found (resource doesn't exist)
- `500` - Internal Server Error

---

## Technology Stack

- **FastAPI** - REST API framework
- **SQLite** - Structured stock data
- **ChromaDB** - Vector database for documents
- **OpenAI GPT-4o-mini** - Natural language processing
- **OpenAI text-embedding-3-small** - Document embeddings
- **Docling** - PDF parsing

---

## License

This project is provided as-is for educational and research purposes.
