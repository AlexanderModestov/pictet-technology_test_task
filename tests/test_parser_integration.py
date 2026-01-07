"""
Simple integration test for the updated PDF parser
"""
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)

# Test imports
print("Testing imports...")
try:
    from app.unstructured.pdf_parser import PDFParser, pdf_parser
    print("[OK] Successfully imported PDFParser and pdf_parser")
except ImportError as e:
    print(f"[FAIL] Import failed: {e}")
    exit(1)

# Test instantiation
print("\nTesting instantiation...")
try:
    parser = PDFParser()
    print("[OK] Successfully instantiated PDFParser with default settings")
except Exception as e:
    print(f"[FAIL] Instantiation failed: {e}")
    exit(1)

# Test with custom settings
print("\nTesting instantiation with custom settings...")
try:
    parser_no_ocr = PDFParser(do_ocr=False, do_table_structure=False)
    print("[OK] Successfully instantiated PDFParser with custom settings")
except Exception as e:
    print(f"[FAIL] Custom instantiation failed: {e}")
    exit(1)

# Test method signatures
print("\nVerifying method signatures...")
methods = ['extract_text_from_pdf', 'extract_metadata', 'get_document_stats', 'validate_pdf']
for method_name in methods:
    if hasattr(parser, method_name):
        print(f"[OK] Method '{method_name}' exists")
    else:
        print(f"[FAIL] Method '{method_name}' missing")
        exit(1)

# Test with a sample PDF if one exists
print("\nLooking for sample PDFs...")
sample_pdf_path = Path("app/src/dummy_report.pdf")
if sample_pdf_path.exists():
    print(f"[OK] Found sample PDF: {sample_pdf_path}")

    print("\nTesting PDF validation...")
    try:
        validation_result = parser.validate_pdf(str(sample_pdf_path))
        print(f"  Validation result: {validation_result}")
        if validation_result.get('valid'):
            print("[OK] PDF validation successful")
        else:
            print(f"[WARN] PDF validation returned False: {validation_result.get('error')}")
    except Exception as e:
        print(f"[FAIL] Validation failed with error: {e}")

    print("\nTesting metadata extraction...")
    try:
        metadata = parser.extract_metadata(str(sample_pdf_path))
        print(f"  Metadata: {metadata}")
        print("[OK] Metadata extraction successful")
    except Exception as e:
        print(f"[FAIL] Metadata extraction failed: {e}")

    print("\nTesting text extraction (this may take a moment)...")
    try:
        pages = parser.extract_text_from_pdf(str(sample_pdf_path))
        print(f"  Extracted {len(pages)} pages")
        if pages:
            print(f"  First page has {pages[0]['char_count']} characters")
        print("[OK] Text extraction successful")
    except Exception as e:
        print(f"[FAIL] Text extraction failed: {e}")
else:
    print(f"[WARN] No sample PDF found at {sample_pdf_path}, skipping live tests")

print("\n" + "="*50)
print("Integration test completed!")
print("="*50)
