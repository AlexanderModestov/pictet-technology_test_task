"""Database connection and schema management for structured stock data"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, BigInteger, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()


class Stock(Base):
    """Stock data model"""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, unique=True, index=True)
    company_name = Column(String(255), nullable=False, index=True)
    isin = Column(String(12), nullable=True)
    sector = Column(String(100), nullable=True, index=True)
    stock_price = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    dividend_yield = Column(Float, nullable=True)
    pe_ratio = Column(Float, nullable=True)
    market_cap = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "company_name": self.company_name,
            "isin": self.isin,
            "sector": self.sector,
            "stock_price": self.stock_price,
            "target_price": self.target_price,
            "dividend_yield": self.dividend_yield,
            "pe_ratio": self.pe_ratio,
            "market_cap": self.market_cap,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DatabaseManager:
    """Manages database connections and operations"""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager

        Args:
            db_path: Path to SQLite database file. If None, uses settings.
        """
        self.db_path = db_path or settings.sqlite_db_path
        self._ensure_db_directory()

        # Create write engine (for admin operations)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=settings.debug,
            connect_args={"check_same_thread": False}  # Needed for SQLite
        )

        # Create READ-ONLY engine for user queries (SECURITY: prevents SQL injection damage)
        self.read_only_engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=settings.debug,
            connect_args={
                "check_same_thread": False,
                "uri": True
            },
            execution_options={"isolation_level": "READ UNCOMMITTED"}
        )

        # Set read-only mode using event listener
        from sqlalchemy import event
        @event.listens_for(self.read_only_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA query_only = ON")
            cursor.close()

        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Create tables
        self._create_tables()

    def _ensure_db_directory(self):
        """Ensure database directory exists"""
        db_path = Path(self.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

    def _create_tables(self):
        """Create database tables if they don't exist"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created/verified")

    def get_session(self) -> Session:
        """
        Get a new database session

        Returns:
            SQLAlchemy session
        """
        return self.SessionLocal()

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute a raw SQL query and return results

        SECURITY: Uses read-only engine to prevent destructive operations.

        Args:
            query: SQL query to execute (must be SELECT only)

        Returns:
            List of dictionaries representing query results
        """
        try:
            # Use read-only engine for user queries (SECURITY LAYER)
            with self.read_only_engine.connect() as connection:
                result = connection.execute(text(query))

                # Get column names
                columns = result.keys()

                # Convert rows to dictionaries
                rows = []
                for row in result:
                    rows.append(dict(zip(columns, row)))

                logger.info(f"Query executed successfully (read-only). Returned {len(rows)} rows.")
                return rows

        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise

    def get_stock_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get stock information by symbol

        Args:
            symbol: Stock ticker symbol

        Returns:
            Stock data as dictionary or None if not found
        """
        session = self.get_session()
        try:
            stock = session.query(Stock).filter(Stock.symbol == symbol.upper()).first()
            return stock.to_dict() if stock else None
        finally:
            session.close()

    def get_all_stocks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all stocks

        Args:
            limit: Maximum number of stocks to return

        Returns:
            List of stock dictionaries
        """
        session = self.get_session()
        try:
            stocks = session.query(Stock).limit(limit).all()
            return [stock.to_dict() for stock in stocks]
        finally:
            session.close()

    def get_stocks_by_sector(self, sector: str) -> List[Dict[str, Any]]:
        """
        Get all stocks in a specific sector

        Args:
            sector: Sector name

        Returns:
            List of stock dictionaries
        """
        session = self.get_session()
        try:
            stocks = session.query(Stock).filter(Stock.sector == sector).all()
            return [stock.to_dict() for stock in stocks]
        finally:
            session.close()

    def get_table_schema(self) -> str:
        """
        Get a human-readable description of the stocks table schema

        Returns:
            Schema description string
        """
        return """
TABLE: stocks
COLUMNS:
- symbol (VARCHAR): Stock ticker symbol (e.g., 'AAPL', 'TSLA')
- company_name (VARCHAR): Full company name
- isin (VARCHAR): International Securities ID
- sector (VARCHAR): Industry sector (e.g., 'Technology', 'Healthcare')
- stock_price (DECIMAL): Current stock price in USD
- target_price (DECIMAL): Analyst target price in USD
- dividend_yield (DECIMAL): Annual dividend yield as percentage
- pe_ratio (DECIMAL): Price-to-Earnings ratio
- market_cap (BIGINT): Market capitalization in USD
        """.strip()

    def health_check(self) -> bool:
        """
        Check if database connection is healthy

        Returns:
            True if healthy, False otherwise
        """
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def close(self):
        """Close database connections"""
        self.engine.dispose()
        self.read_only_engine.dispose()
        logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()
