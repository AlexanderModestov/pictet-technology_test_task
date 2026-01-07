"""PDF document parsing and text extraction using Docling"""

import logging
from pathlib import Path
from typing import List, Dict, Any

from docling.backend.docling_parse_v2_backend import DoclingParseV2DocumentBackend
from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode, EasyOcrOptions
from docling.document_converter import DocumentConverter, FormatOption
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline

from app.utils.helpers import clean_text

logger = logging.getLogger(__name__)


class PDFParser:
    """Handles PDF document parsing and text extraction using Docling"""

    def __init__(
        self,
        pdf_backend=DoclingParseV2DocumentBackend,
        do_ocr: bool = True,
        do_table_structure: bool = True,
        ocr_lang: List[str] = None
    ):
        """
        Initialize PDF parser with Docling

        Args:
            pdf_backend: Docling backend to use for PDF parsing
            do_ocr: Whether to perform OCR on images and scanned documents
            do_table_structure: Whether to extract table structures
            ocr_lang: List of languages for OCR (default: ['en'])
        """
        self.pdf_backend = pdf_backend
        self.do_ocr = do_ocr
        self.do_table_structure = do_table_structure
        self.ocr_lang = ocr_lang or ['en']
        self.doc_converter = self._create_document_converter()

    def _create_document_converter(self) -> DocumentConverter:
        """Creates and returns a DocumentConverter with configured pipeline options."""
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = self.do_ocr

        if self.do_ocr:
            ocr_options = EasyOcrOptions(lang=self.ocr_lang, force_full_page_ocr=False)
            pipeline_options.ocr_options = ocr_options

        pipeline_options.do_table_structure = self.do_table_structure
        if self.do_table_structure:
            pipeline_options.table_structure_options.do_cell_matching = True
            pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

        format_options = {
            InputFormat.PDF: FormatOption(
                pipeline_cls=StandardPdfPipeline,
                pipeline_options=pipeline_options,
                backend=self.pdf_backend
            )
        }

        return DocumentConverter(format_options=format_options)

    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from PDF file, preserving page structure

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of dictionaries with page information:
            [
                {
                    "page_number": int,
                    "text": str,
                    "char_count": int
                },
                ...
            ]
        """
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info(f"Extracting text from PDF using Docling: {pdf_path}")

        pages = []

        try:
            # Convert document using Docling
            conv_result = self.doc_converter.convert(pdf_file)

            if conv_result.status != ConversionStatus.SUCCESS:
                logger.error(f"Failed to convert PDF: {pdf_path}")
                raise RuntimeError(f"Document conversion failed with status: {conv_result.status}")

            # Export to markdown format (preserves structure)
            markdown_text = conv_result.document.export_to_markdown()

            # Export to dict to get page information
            doc_dict = conv_result.document.export_to_dict()

            # Extract text per page
            if 'pages' in doc_dict:
                for page_info in doc_dict['pages']:
                    page_num = page_info.get('page_no', 0)

                    # Collect all text from this page
                    page_text = self._extract_page_text(doc_dict, page_num)

                    if page_text.strip():
                        pages.append({
                            "page_number": page_num,
                            "text": page_text,
                            "char_count": len(page_text)
                        })
            else:
                # Fallback: use entire markdown as single page
                logger.warning(f"No page information found, using full document text")
                pages.append({
                    "page_number": 1,
                    "text": markdown_text,
                    "char_count": len(markdown_text)
                })

            logger.info(f"Extracted {len(pages)} pages from {pdf_path}")

        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise

        return pages

    def _extract_page_text(self, doc_dict: Dict[str, Any], page_num: int) -> str:
        """
        Extract all text from a specific page number

        Args:
            doc_dict: Document dictionary from Docling
            page_num: Page number to extract

        Returns:
            Concatenated text from the page
        """
        page_texts = []

        # Extract text blocks for this page
        if 'texts' in doc_dict:
            for text_item in doc_dict['texts']:
                if 'prov' in text_item and text_item['prov']:
                    if text_item['prov'][0].get('page_no') == page_num:
                        text_content = text_item.get('text', '')
                        if text_content:
                            page_texts.append(text_content)

        # Extract table text for this page
        if 'tables' in doc_dict:
            for table_item in doc_dict['tables']:
                if 'prov' in table_item and table_item['prov']:
                    if table_item['prov'][0].get('page_no') == page_num:
                        # Convert table to text representation
                        table_text = self._table_to_text(table_item)
                        if table_text:
                            page_texts.append(table_text)

        # Combine all text from the page
        combined_text = '\n\n'.join(page_texts)
        return self._clean_pdf_text(combined_text)

    def _table_to_text(self, table_item: Dict[str, Any]) -> str:
        """
        Convert table data to text representation

        Args:
            table_item: Table item from document dictionary

        Returns:
            Text representation of table
        """
        if 'data' not in table_item or 'grid' not in table_item['data']:
            return ""

        table_lines = []
        for row in table_item['data']['grid']:
            row_texts = [cell.get('text', '') for cell in row]
            table_lines.append(' | '.join(row_texts))

        return '\n'.join(table_lines)

    def _clean_pdf_text(self, text: str) -> str:
        """
        Clean extracted PDF text

        Args:
            text: Raw PDF text

        Returns:
            Cleaned text
        """
        # Remove common PDF artifacts
        text = text.replace("\x00", "")  # Null bytes
        text = text.replace("\ufffd", "")  # Replacement character

        # Normalize whitespace
        text = clean_text(text)

        return text

    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract metadata from PDF using Docling

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with PDF metadata
        """
        try:
            pdf_file = Path(pdf_path)
            conv_result = self.doc_converter.convert(pdf_file)

            if conv_result.status != ConversionStatus.SUCCESS:
                logger.error(f"Failed to convert PDF for metadata extraction: {pdf_path}")
                return {}

            doc_dict = conv_result.document.export_to_dict()

            # Extract metadata from Docling document
            origin = doc_dict.get('origin', {})
            metadata = {
                "title": doc_dict.get('name', ''),
                "filename": origin.get('filename', ''),
                "page_count": len(doc_dict.get('pages', [])),
                "text_blocks": len(doc_dict.get('texts', [])),
                "tables": len(doc_dict.get('tables', [])),
                "pictures": len(doc_dict.get('pictures', [])),
            }

            return metadata
        except Exception as e:
            logger.error(f"Error extracting PDF metadata: {e}")
            return {}

    def get_document_stats(self, pdf_path: str) -> Dict[str, Any]:
        """
        Get statistics about PDF document

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with document statistics
        """
        try:
            pages = self.extract_text_from_pdf(pdf_path)
            total_chars = sum(p["char_count"] for p in pages)
            avg_chars_per_page = total_chars / len(pages) if pages else 0

            return {
                "total_pages": len(pages),
                "total_characters": total_chars,
                "avg_characters_per_page": avg_chars_per_page,
                "estimated_tokens": total_chars // 4  # Rough estimate
            }
        except Exception as e:
            logger.error(f"Error getting document stats: {e}")
            return {}

    def validate_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Validate PDF file using Docling

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with validation results
        """
        pdf_file = Path(pdf_path)

        if not pdf_file.exists():
            return {
                "valid": False,
                "error": f"File not found: {pdf_path}"
            }

        if pdf_file.suffix.lower() != ".pdf":
            return {
                "valid": False,
                "error": "File is not a PDF"
            }

        try:
            conv_result = self.doc_converter.convert(pdf_file)

            if conv_result.status != ConversionStatus.SUCCESS:
                return {
                    "valid": False,
                    "error": f"Failed to convert PDF: {conv_result.status}"
                }

            doc_dict = conv_result.document.export_to_dict()
            page_count = len(doc_dict.get('pages', []))

            if page_count == 0:
                return {
                    "valid": False,
                    "error": "PDF has no pages"
                }

            return {
                "valid": True,
                "page_count": page_count
            }

        except Exception as e:
            return {
                "valid": False,
                "error": f"Failed to validate PDF: {str(e)}"
            }


# Global PDF parser instance
pdf_parser = PDFParser()
