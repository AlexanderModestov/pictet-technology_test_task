"""CSV/Excel data ingestion for stock information"""

import logging
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from sqlalchemy.exc import IntegrityError

from app.structured.database import Stock, db_manager
from app.utils.helpers import safe_float, safe_int

logger = logging.getLogger(__name__)


class CSVIngester:
    """Handles CSV/Excel file parsing and database ingestion"""

    # Column mapping for different file formats
    COLUMN_MAPPINGS = {
        'equities': {
            'Ticker': 'symbol',
            'Company': 'company_name',
            'ISIN': 'isin',
            'Sector - Level 1': 'sector',
            'Price': 'stock_price',
            'Target Price': 'target_price',
            'Dividend Yield': 'dividend_yield',
            'Price to Earning Forward 12M': 'pe_ratio',
            'Market Capitalization': 'market_cap'
        },
        'investment_research': {
            'Ticker': 'symbol',
            'Company Description': 'company_name',
            'ISIN': 'isin',
            'Sector - Level 1': 'sector',
            'Price': 'stock_price',
            'Target Price': 'target_price',
            'Dividend Yield': 'dividend_yield',
            'Price to Earning Forward 12M': 'pe_ratio',
            'Market Capitalization': 'market_cap'
        }
    }

    def __init__(self, database_manager=None):
        """
        Initialize CSV ingester

        Args:
            database_manager: DatabaseManager instance. If None, uses global instance.
        """
        self.db_manager = database_manager or db_manager

    def ingest_file(self, file_path: str, column_mapping: str = None) -> Dict[str, int]:
        """
        Ingest stocks from CSV or Excel file into database

        Args:
            file_path: Path to CSV or Excel file
            column_mapping: Name of column mapping to use ('equities' or None for default)

        Returns:
            Dictionary with statistics
        """
        return self.ingest_csv(file_path, column_mapping)

    def ingest_csv(self, csv_path: str, column_mapping: str = None) -> Dict[str, int]:
        """
        Ingest stocks from CSV or Excel file into database

        Args:
            csv_path: Path to CSV or Excel file
            column_mapping: Name of column mapping to use ('equities' or None for default)

        Returns:
            Dictionary with statistics: {
                'processed': int,
                'inserted': int,
                'updated': int,
                'failed': int
            }
        """
        file_path = Path(csv_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {csv_path}")

        logger.info(f"Starting data ingestion from {csv_path}")

        # Read file (CSV or Excel)
        try:
            if file_path.suffix.lower() in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
                logger.info(f"Read Excel file with {len(df)} rows")
            else:
                df = pd.read_csv(file_path)
                logger.info(f"Read CSV file with {len(df)} rows")
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            raise

        # Apply column mapping if specified
        if column_mapping and column_mapping in self.COLUMN_MAPPINGS:
            mapping = self.COLUMN_MAPPINGS[column_mapping]
            logger.info(f"Applying '{column_mapping}' column mapping")
            df = df.rename(columns=mapping)
            logger.info(f"Columns after mapping: {list(df.columns)[:10]}...")

        # Validate required columns
        required_columns = {'symbol', 'company_name'}
        if not required_columns.issubset(set(df.columns)):
            available_cols = list(df.columns)[:20]
            raise ValueError(
                f"File must contain columns: {required_columns}. "
                f"Available columns: {available_cols}... "
                f"(Use column_mapping='equities' for equities.xlsx format)"
            )

        # Filter out rows with missing symbol or company_name
        initial_count = len(df)
        df = df.dropna(subset=['symbol', 'company_name'])
        filtered_count = initial_count - len(df)
        if filtered_count > 0:
            logger.info(f"Filtered out {filtered_count} rows with missing symbol/company_name")

        stats = {
            'processed': 0,
            'inserted': 0,
            'updated': 0,
            'failed': 0,
            'skipped': filtered_count
        }

        # Process each row
        session = self.db_manager.get_session()
        try:
            for idx, row in df.iterrows():
                try:
                    stats['processed'] += 1
                    result = self._process_row(session, row)
                    if result == 'inserted':
                        stats['inserted'] += 1
                    elif result == 'updated':
                        stats['updated'] += 1

                    # Log progress for large files
                    if stats['processed'] % 100 == 0:
                        logger.info(f"Processed {stats['processed']}/{len(df)} rows...")

                except Exception as e:
                    stats['failed'] += 1
                    logger.warning(f"Failed to process row {stats['processed']}: {e}")

            session.commit()
            logger.info(f"CSV ingestion complete. Stats: {stats}")

        except Exception as e:
            session.rollback()
            logger.error(f"Error during CSV ingestion: {e}")
            raise
        finally:
            session.close()

        return stats

    def _process_row(self, session, row: pd.Series) -> str:
        """
        Process a single row from CSV

        Args:
            session: Database session
            row: Pandas Series representing a row

        Returns:
            'inserted' or 'updated'
        """
        symbol = str(row['symbol']).strip().upper()

        # Check if stock already exists
        existing_stock = session.query(Stock).filter(Stock.symbol == symbol).first()

        # Prepare stock data
        stock_data = {
            'symbol': symbol,
            'company_name': str(row['company_name']).strip(),
            'isin': str(row.get('isin', '')).strip() or None,
            'sector': str(row.get('sector', '')).strip() or None,
            'stock_price': safe_float(row.get('stock_price'), None),
            'target_price': safe_float(row.get('target_price'), None),
            'dividend_yield': safe_float(row.get('dividend_yield'), None),
            'pe_ratio': safe_float(row.get('pe_ratio'), None),
            'market_cap': safe_int(row.get('market_cap'), None),
        }

        if existing_stock:
            # Update existing stock
            for key, value in stock_data.items():
                if key != 'symbol':  # Don't update symbol
                    setattr(existing_stock, key, value)
            return 'updated'
        else:
            # Insert new stock
            new_stock = Stock(**stock_data)
            session.add(new_stock)
            return 'inserted'

    def validate_csv_format(self, csv_path: str) -> Dict[str, any]:
        """
        Validate CSV file format without ingesting

        Args:
            csv_path: Path to CSV file

        Returns:
            Dictionary with validation results
        """
        csv_file = Path(csv_path)
        if not csv_file.exists():
            return {
                'valid': False,
                'error': f"File not found: {csv_path}"
            }

        try:
            df = pd.read_csv(csv_file)
        except Exception as e:
            return {
                'valid': False,
                'error': f"Failed to read CSV: {str(e)}"
            }

        required_columns = {'symbol', 'company_name'}
        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            return {
                'valid': False,
                'error': f"Missing required columns: {missing_columns}"
            }

        return {
            'valid': True,
            'rows': len(df),
            'columns': list(df.columns)
        }


# Global CSV ingester instance
csv_ingester = CSVIngester()
