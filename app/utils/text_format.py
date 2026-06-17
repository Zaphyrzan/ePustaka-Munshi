"""Text formatting helpers.

The school requires catalogued book records to be stored in UPPERCASE, so
both the CRUD catalog routes and the OCR commit pipeline normalise the
descriptive bibliographic fields through here.
"""


def to_caps(value):
    """Uppercase a string, leaving None/empty untouched."""
    if value is None:
        return None
    s = str(value).strip()
    return s.upper() if s else (None if value == '' else value)


# Book fields that should be stored in uppercase (descriptive text).
# ISBN, call number, language, year, price and description are left as-is.
BOOK_CAPS_FIELDS = ('title', 'author', 'publisher', 'category')
