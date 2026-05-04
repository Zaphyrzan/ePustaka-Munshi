"""
Barcode and Accession Number generation utilities
"""
from datetime import datetime
from app import db
from app.models import BookCopy


def generate_accession_number():
    """
    Generate a sequential accession number
    Format: ACC-YYYY-0001 (e.g., ACC-2024-0001)
    """
    current_year = datetime.utcnow().year
    
    # Find the highest accession number for the current year
    latest_copy = BookCopy.query.filter(
        BookCopy.accession_number.like(f'ACC-{current_year}-%')
    ).order_by(BookCopy.accession_number.desc()).first()
    
    if latest_copy:
        # Extract the number from the accession number
        parts = latest_copy.accession_number.split('-')
        try:
            last_number = int(parts[-1])
            next_number = last_number + 1
        except (ValueError, IndexError):
            next_number = 1
    else:
        next_number = 1
    
    # Format: ACC-2024-0001
    accession_number = f'ACC-{current_year}-{next_number:04d}'
    return accession_number


def generate_barcode(accession_number):
    """
    Generate barcode value from accession number
    For 1D barcodes, we simply use the accession number as the barcode value
    The actual barcode image can be generated when needed using python-barcode
    
    Args:
        accession_number: The accession number (e.g., ACC-2024-0001)
    
    Returns:
        barcode_value: A scannable barcode value
    """
    # Remove hyphens for barcode scanning (most 1D scanners output without formatting)
    # This makes it easier to scan and process
    barcode_value = accession_number.replace('-', '')
    return barcode_value


def create_barcode_image(accession_number, filepath):
    """
    Generate a barcode image file for printing
    
    Args:
        accession_number: The accession number
        filepath: Where to save the barcode image
    
    Returns:
        filepath: Path to the generated barcode image
    """
    import barcode
    from barcode.writer import ImageWriter
    
    barcode_value = generate_barcode(accession_number)
    
    # Use CODE128 format - widely compatible with 1D scanners
    ean = barcode.get_barcode_class('code128')
    ean_instance = ean(barcode_value, writer=ImageWriter())
    
    # Save without extension (barcode library adds .png)
    ean_instance.save(filepath.replace('.png', ''))
    
    return filepath
