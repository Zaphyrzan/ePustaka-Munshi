"""
Vision OCR Service - Claude vision API for handwritten ledger digitization.

Tesseract (OCRService) only reads printed text, but the school's "Daftar
Buku-Buku Perpustakaan" ledgers are handwritten. This service sends each
scanned page to a Claude vision model and gets back structured rows in the
same Malaysian ledger format. It returns the same dict shape as
OCRService.process_file(), so the rest of the pipeline (staging, review,
commit) works unchanged with either engine.
"""
import os
import io
import json
import base64

from PIL import Image

# Anthropic SDK (Claude API)
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# PDF support
try:
    from pdf2image import convert_from_path
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# Tesseract is optional here - only used to auto-detect page rotation (OSD)
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


# Default model: Haiku keeps the full ~300-page digitization around USD $5.
# Override with the OCR_VISION_MODEL env var (e.g. claude-opus-4-8) if a
# batch of pages needs more accuracy.
DEFAULT_MODEL = 'claude-haiku-4-5'

# Long edge for page images sent to the API. Larger images cost more tokens
# without improving accuracy at this model tier.
MAX_IMAGE_EDGE = 1568

# JSON schema enforced via structured outputs, so every response is
# guaranteed-parseable JSON (no regex scraping of model text).
_ROW_PROPS = {
    'no_perolehan': {'type': ['string', 'null']},
    'no_panggilan': {'type': ['string', 'null']},
    'pengarang': {'type': ['string', 'null']},
    'tajuk_buku': {'type': ['string', 'null']},
    'penerbit': {'type': ['string', 'null']},
    'tarikh_penerbit': {'type': ['string', 'null']},
    'tarikh_perolehan': {'type': ['string', 'null']},
    'bil_no': {'type': ['string', 'null']},
    'punca': {'type': ['string', 'null']},
    'harga_rm': {'type': ['string', 'null']},
    'harga_sen': {'type': ['string', 'null']},
    'muka_surat': {'type': ['string', 'null']},
    'catatan': {'type': ['string', 'null']},
    'confidence': {'type': 'number'},
}

LEDGER_SCHEMA = {
    'type': 'object',
    'properties': {
        'rows': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': _ROW_PROPS,
                'required': list(_ROW_PROPS.keys()),
                'additionalProperties': False,
            },
        },
    },
    'required': ['rows'],
    'additionalProperties': False,
}

SYSTEM_PROMPT = """You are digitizing handwritten Malaysian school library acquisition ledgers ("Daftar Buku-Buku Perpustakaan").

Each page is a table with these columns (left to right):
No. Perolehan (accession number) | No. Panggilan (call number) | Pengarang (author) | Tajuk Buku (title) | Tempat dan Nama Penerbit (place & publisher) | Tarikh Penerbit (publication year) | Tarikh Perolehan (acquisition date) | Bil. No. | Punca (source, e.g. PCG, KPM, Pembelian) | Harga RM / sen (price) | Muka Surat (page count) | Catatan (notes)

Transcribe EVERY data row on the page. Rules:
- The page may be scanned rotated (90 or 180 degrees) - read it in whatever orientation the table is legible.
- Ditto marks (" or ,, or 'sda') mean "same as the row above" - copy the value from the previous row.
- Transcribe handwriting faithfully; do not translate or normalise spelling.
- Use null for genuinely empty cells. If a cell is present but illegible, transcribe your best guess and lower that row's confidence.
- harga_rm and harga_sen are the two halves of the price column; keep them as written.
- confidence is 0.0-1.0 for how certain you are about the whole row.
- Skip header rows, the page summary boxes (ANALISA / KELAS BUKU / JUMLAH), and fully empty rows."""

USER_PROMPT = 'Extract all ledger rows from this page.'


def _find_poppler():
    """Locate the Poppler binaries pdf2image needs on Windows"""
    locations = [
        r"C:\Users\wanza\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin",
        r"C:\Program Files\poppler\bin",
        r"C:\Program Files\poppler-24.02.0\Library\bin",
        r"C:\poppler\bin",
    ]
    for loc in locations:
        if os.path.exists(os.path.join(loc, "pdftoppm.exe")):
            return loc
    return None  # assume it's on PATH


class VisionOCRService:
    """Handwriting-capable OCR backend using the Claude vision API"""

    def __init__(self, api_key=None, model=None, tesseract_cmd=None):
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        self.model = model or os.environ.get('OCR_VISION_MODEL', DEFAULT_MODEL)
        if TESSERACT_AVAILABLE:
            # Fall back to the standard Windows install path when not on PATH
            default_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            if not tesseract_cmd and os.path.exists(default_cmd):
                tesseract_cmd = default_cmd
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self._client = None

    def is_available(self):
        """True when the SDK is installed and an API key is configured"""
        return ANTHROPIC_AVAILABLE and bool(self.api_key)

    @property
    def client(self):
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    # ============ Image preparation ============

    def _auto_rotate(self, image):
        """Fix page rotation using Tesseract orientation detection (OSD).

        The printed headers on the ledger are enough for OSD even though the
        body is handwritten. If OSD is unavailable or fails, the image is
        sent as-is - the prompt tells the model the page may be rotated.
        """
        if not TESSERACT_AVAILABLE:
            return image
        try:
            osd = pytesseract.image_to_osd(image)
            for line in osd.splitlines():
                if line.startswith('Rotate:'):
                    angle = int(line.split(':')[1].strip())
                    if angle:
                        # PIL rotates counter-clockwise; OSD angle is the CW
                        # rotation needed to make the text upright
                        image = image.rotate(-angle, expand=True)
                    break
        except Exception:
            return image

        # OSD picks the wrong direction on handwriting-heavy pages (90 vs
        # 270), so disambiguate by OCR-ing the PRINTED form headers - they
        # only read correctly when the page is upright.
        if self._header_score(image) < self._header_score(image.rotate(180, expand=True)):
            image = image.rotate(180, expand=True)
        return image

    @staticmethod
    def _header_score(image):
        """Count printed ledger-header keywords Tesseract can read at this orientation"""
        keywords = ['daftar', 'perpustakaan', 'perolehan', 'panggilan', 'pengarang',
                    'tajuk', 'penerbit', 'punca', 'catatan', 'muka surat', 'harga', 'analisa']
        # Downscale for speed - headers are large enough to survive it
        small = image.copy()
        small.thumbnail((1200, 1200))
        try:
            text = pytesseract.image_to_string(small).lower()
        except Exception:
            return 0
        return sum(1 for kw in keywords if kw in text)

    def _encode_image(self, image):
        """Rotate, downscale and JPEG-encode a page image for the API"""
        image = self._auto_rotate(image)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Downscale to control image token cost
        long_edge = max(image.size)
        if long_edge > MAX_IMAGE_EDGE:
            scale = MAX_IMAGE_EDGE / long_edge
            image = image.resize(
                (int(image.width * scale), int(image.height * scale)),
                Image.Resampling.LANCZOS,
            )

        buf = io.BytesIO()
        image.save(buf, format='JPEG', quality=85)
        return base64.standard_b64encode(buf.getvalue()).decode('utf-8')

    # ============ Extraction ============

    def extract_page(self, image):
        """Send one page image to Claude and return its ledger rows"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            output_config={'format': {'type': 'json_schema', 'schema': LEDGER_SCHEMA}},
            messages=[{
                'role': 'user',
                'content': [
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': 'image/jpeg',
                            'data': self._encode_image(image),
                        },
                    },
                    {'type': 'text', 'text': USER_PROMPT},
                ],
            }],
        )
        # Structured outputs guarantee the first text block is valid JSON
        text = next(b.text for b in response.content if b.type == 'text')
        return json.loads(text).get('rows', [])

    def process_file(self, file_path):
        """Process an image or PDF; returns the same shape as OCRService.process_file"""
        if not self.is_available():
            raise RuntimeError(
                'Vision OCR is not available. Install the anthropic package '
                'and set ANTHROPIC_API_KEY.'
            )

        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            if not PDF_SUPPORT:
                raise RuntimeError('PDF support not available. Install pdf2image and poppler.')
            images = convert_from_path(file_path, dpi=200, poppler_path=_find_poppler())
        else:
            images = [Image.open(file_path)]

        all_rows = []
        for page_num, image in enumerate(images, 1):
            all_rows.extend(self.process_page(image, page_num))

        return {
            'pages': len(images),
            'total_rows': len(all_rows),
            'rows': all_rows,
        }

    def process_page(self, image, page_num):
        """Extract one page and return row dicts in the pipeline's standard shape"""
        rows = []
        for row_num, row in enumerate(self.extract_page(image), 1):
            rows.append({
                'page_number': page_num,
                'row_number': row_num,
                # Reconstructed row text kept for the review UI raw view
                'raw_text': ' | '.join(
                    str(row.get(f) or '') for f in _ROW_PROPS if f != 'confidence'
                ),
                'no_perolehan': row.get('no_perolehan'),
                'no_panggilan': row.get('no_panggilan'),
                'pengarang': row.get('pengarang'),
                'tajuk_buku': row.get('tajuk_buku'),
                'penerbit': row.get('penerbit'),
                'tarikh_penerbit': row.get('tarikh_penerbit'),
                'tarikh_perolehan': row.get('tarikh_perolehan'),
                'bil_no': row.get('bil_no'),
                'punca': row.get('punca'),
                'harga_rm': row.get('harga_rm'),
                'harga_sen': row.get('harga_sen'),
                'muka_surat': row.get('muka_surat'),
                'catatan': row.get('catatan'),
                'confidence': row.get('confidence') or 0.0,
                'confidence_details': {},
            })
        return rows
