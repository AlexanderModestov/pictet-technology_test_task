
# Stock Investment Research Assistant

A GenAI-powered assistant that combines structured stock data (CSV/Excel) and unstructured macroeconomic documents (PDF) to provide comprehensive investment research answers.

## Features

- **RAG Pipeline**: Retrieves relevant information from PDF documents using vector search
- **Text-to-SQL**: Queries structured stock data using natural language
- **Flexible Data Ingestion**: Supports both CSV and Excel (.xlsx) files with custom column mappings
- **Hybrid Responses**: Intelligently combines both data sources
- **Source Attribution**: Tracks and cites information sources
- **REST API**: FastAPI-based interface for easy integration

## Architecture

The system uses:
- **FastAPI** for the REST API
- **SQLite** for structured stock data storage
- **ChromaDB** for vector-based document search
- **OpenAI GPT-4o-mini** for query classification and response generation
- **OpenAI text-embedding-3-small** for document embeddings

## Prerequisites

- Python 3.9+
- OpenAI API key
- Git (optional)

## Installation

### 1. Clone or Download the Repository

```bash
git clone <repository-url>
cd TestTask
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```ini
OPENAI_API_KEY=sk-your-api-key-here
```

## Quick Start

### 1. Load Stock Data

The system supports both CSV and Excel (.xlsx) files for stock data ingestion.

#### Option A: Load from Excel file (equities.xlsx)

If you have the `data/equities.xlsx` file, load it using the 'equities' column mapping:

```python
python -c "from app.structured.csv_ingester import csv_ingester; csv_ingester.ingest_file('data/equities.xlsx', column_mapping='equities')"
```

#### Option B: Load from CSV file (stocks.csv)

Create a CSV file at `data/stocks.csv` with stock information (see example below), then run:

```python
python -c "from app.structured.csv_ingester import csv_ingester; csv_ingester.ingest_csv('data/stocks.csv')"
```

### 2. Upload PDF Documents (Optional)

Place PDF documents in `data/pdfs/` directory. They will be indexed when you upload them via the API.

### 3. Start the API Server

```bash
python -m app.main
```

Or using uvicorn directly:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

### 4. Access Interactive Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Usage Examples

### Using the API

#### 1. Health Check

```bash
curl http://localhost:8000/api/v1/health
```

#### 2. Query Stock Data

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is Tesla'\''s P/E ratio?",
    "include_sources": true
  }'
```

#### 3. Upload PDF Document

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -F "file=@data/pdfs/market_report.pdf" \
  -F "doc_type=market_analysis"
```

#### 4. Upload Stock CSV

Note: The API endpoint only accepts CSV files. For Excel files, use direct Python ingestion.

```bash
curl -X POST http://localhost:8000/api/v1/stocks \
  -F "file=@data/stocks.csv"
```

#### 5. List Documents

```bash
curl http://localhost:8000/api/v1/documents
```

### Using Python Client

```python
import requests

# Query the assistant
response = requests.post(
    "http://localhost:8000/api/v1/query",
    json={
        "question": "How might inflation affect tech stocks?",
        "include_sources": True
    }
)

print(response.json()["answer"])
```

## Sample Data Format

### Stock CSV Format

Create `data/stocks.csv`:

```csv
symbol,company_name,isin,sector,stock_price,target_price,dividend_yield,pe_ratio,market_cap
AAPL,Apple Inc.,US0378331005,Technology,178.50,195.00,0.52,29.5,2800000000000
TSLA,Tesla Inc.,US88160R1014,Automotive,217.50,250.00,0.00,52.3,690000000000
MSFT,Microsoft Corporation,US5949181045,Technology,378.90,425.00,0.78,35.2,2810000000000
```

Required columns:
- `symbol` (required): Stock ticker
- `company_name` (required): Company name
- Other columns are optional

### Stock Excel Format (equities.xlsx)

The system supports Excel files with custom column mappings. The `equities.xlsx` file uses these columns:

| Excel Column Name | Database Field | Description |
|------------------|----------------|-------------|
| Ticker | symbol | Stock ticker symbol |
| Company | company_name | Company name |
| ISIN | isin | International Securities Identification Number |
| Sector - Level 1 | sector | Company sector |
| Price | stock_price | Current stock price |
| Target Price | target_price | Analyst target price |
| Dividend Yield | dividend_yield | Dividend yield percentage |
| Price to Earning Forward 12M | pe_ratio | Forward P/E ratio |
| Market Capitalization | market_cap | Market capitalization |

To load Excel files with different column names, use the `column_mapping='equities'` parameter:

```python
from app.structured.csv_ingester import csv_ingester
csv_ingester.ingest_file('data/equities.xlsx', column_mapping='equities')
```

## Example Queries

### Structured Queries (SQL-based)
- "What is Apple's stock price?"
- "List all stocks in the Technology sector"
- "Which stock has the highest dividend yield?"
- "Compare P/E ratios of AAPL and MSFT"

### Unstructured Queries (Document-based)
- "What are the current inflation trends?"
- "How is the Fed approaching interest rates?"
- "What factors affect tech sector performance?"

### Hybrid Queries (Both sources)
- "How might inflation affect Tesla stock?"
- "Should I invest in tech stocks given current market conditions?"
- "Which sectors perform well in high interest rate environments?"

## Project Structure

```
TestTask/
├── app/
│   ├── api/              # API routes and schemas
│   ├── core/             # Business logic (classifier, generator)
│   ├── structured/       # SQL, CSV, and Excel handling
│   │   ├── csv_ingester.py  # Handles CSV/Excel ingestion
│   │   ├── database.py      # SQLAlchemy database models
│   │   └── text_to_sql.py   # Natural language to SQL
│   ├── unstructured/     # PDF processing and RAG
│   ├── utils/            # Helper functions
│   ├── config.py         # Configuration management
│   └── main.py           # FastAPI application
├── data/
│   ├── pdfs/             # PDF documents
│   ├── stocks.csv        # Stock data (CSV format)
│   ├── equities.xlsx     # Stock data (Excel format)
│   ├── stocks.db         # SQLite database (auto-created)
│   └── chroma/           # ChromaDB vector store (auto-created)
├── tests/                # Test suite
├── requirements.txt      # Dependencies
├── .env.example          # Environment template
└── README.md             # This file
```

## Data Ingestion Features

### CSV/Excel Ingester

The `csv_ingester` module (`app/structured/csv_ingester.py`) provides flexible data ingestion:

- **Multiple file formats**: Supports both CSV (.csv) and Excel (.xlsx, .xls) files
- **Column mapping**: Automatic column name translation for different file formats
- **Upsert logic**: Updates existing stocks or inserts new ones based on symbol
- **Validation**: Validates required columns and data types
- **Error handling**: Continues processing even if individual rows fail
- **Statistics reporting**: Provides detailed ingestion statistics

#### Column Mappings

The ingester supports predefined column mappings for different file formats:

- **'equities'**: Maps columns from equities.xlsx format (Ticker → symbol, Company → company_name, etc.)
- **default**: Standard format (symbol, company_name, etc.)

#### Direct Python Usage

```python
from app.structured.csv_ingester import csv_ingester

# Load CSV file (no mapping needed)
stats = csv_ingester.ingest_csv('data/stocks.csv')

# Load Excel file with column mapping
stats = csv_ingester.ingest_file('data/equities.xlsx', column_mapping='equities')

# View statistics
print(f"Processed: {stats['processed']}")
print(f"Inserted: {stats['inserted']}")
print(f"Updated: {stats['updated']}")
print(f"Failed: {stats['failed']}")
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_text_to_sql.py

# Run with coverage
pytest --cov=app tests/
```

## Configuration

All configuration is managed through environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `LLM_MODEL` | LLM model to use | gpt-4o-mini |
| `EMBEDDING_MODEL` | Embedding model | text-embedding-3-small |
| `SQLITE_DB_PATH` | SQLite database path | ./data/stocks.db |
| `CHROMA_PERSIST_PATH` | ChromaDB storage | ./data/chroma |
| `API_HOST` | API host | 0.0.0.0 |
| `API_PORT` | API port | 8000 |
| `CHUNK_SIZE` | Chunk size in tokens | 512 |
| `TOP_K_RESULTS` | Vector search results | 5 |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/query` | Submit question |
| POST | `/api/v1/documents` | Upload PDF |
| GET | `/api/v1/documents` | List documents |
| DELETE | `/api/v1/documents/{filename}` | Delete document |
| POST | `/api/v1/stocks` | Upload stock CSV (CSV only, use Python for Excel) |

## Troubleshooting

### Common Issues

1. **ImportError: No module named 'app'**
   - Make sure you're running from the project root directory
   - Try: `python -m app.main` instead of `python app/main.py`

2. **OpenAI API errors**
   - Verify your API key is correct in `.env`
   - Check your OpenAI account has available credits
   - Ensure you have access to the specified models

3. **ChromaDB errors**
   - Delete `data/chroma/` directory and restart
   - Check disk space and permissions

4. **SQL errors**
   - Delete `data/stocks.db` and re-import CSV/Excel
   - Check file format matches expected schema

5. **Excel file ingestion errors**
   - Error: "File must contain columns: {'symbol', 'company_name'}"
     - Solution: Use `column_mapping='equities'` parameter for equities.xlsx format
     - Example: `csv_ingester.ingest_file('data/equities.xlsx', column_mapping='equities')`
   - Error: "No module named 'openpyxl'"
     - Solution: Install dependencies with `pip install -r requirements.txt`
     - The openpyxl library is required for reading Excel files

6. **CSV/Excel file format issues**
   - Ensure Excel files are saved as .xlsx or .xls (not .xlsb or other formats)
   - Check that required columns (symbol, company_name) are present
   - Verify numeric columns contain valid numbers (not text)
   - Remove or fix rows with missing symbol or company_name values

## Performance Optimization

- **Batch Processing**: Upload multiple documents at once
- **Caching**: Results are cached in ChromaDB for faster retrieval
- **Index Optimization**: Database indices on frequently queried columns

## Security Considerations

- Never commit `.env` file with real API keys
- In production, use proper authentication/authorization
- Validate all user inputs (implemented with Pydantic)
- SQL injection protection (implemented with parameterized queries)

## License

This project is provided as-is for educational and research purposes.

## Support

For issues and questions, please check:
1. This README
2. API documentation at `/docs`
3. Test files for usage examples
