# ePustaka Munshi — Smart Library System

A full-stack library management system for a Malaysian secondary school (SMK Abdullah Munshi), built to replace a handwritten paper ledger. Its headline feature is **digitizing the school's handwritten acquisition ledger with a vision LLM**, benchmarked against a traditional OCR baseline.

**Live demo:** https://epustaka-munshi.vercel.app
**Stack:** React + TypeScript · Flask (Python) · Supabase (PostgreSQL) · Anthropic Claude Vision · Vercel

> Final Year Project — B.Sc. Software Engineering, Universiti Teknologi Malaysia.

<!-- Add screenshots here (login, dashboard, OCR review, circulation) for the best first impression. -->

---

## What it does

- **Catalog & inventory** — books with multiple physical copies, each tracked by accession number, barcode, status, condition, and shelf location.
- **Circulation** — barcode checkout/return, 7-day loans with one renewal, overdue tracking, and loan history with the staff handler.
- **Members & roles** — borrowers (student, staff, external) and operators (Administrator, Librarian, Library Prefect) with role-based permissions. Students can be promoted to Library Prefect and demoted back.
- **Ledger OCR** — upload a scanned page of the handwritten ledger; a vision LLM reads it and extracts structured fields with a per-row confidence score; staff verify each row against the source image before committing it to the catalog. ~2,000 real ledger rows digitized.
- **Bilingual UI** — English / Bahasa Melayu.

## OCR pipeline (the novel part)

Traditional OCR (Tesseract) could not reliably read the decades-old cursive handwriting, so the system uses **Anthropic's Claude vision model** as the primary OCR engine and keeps **Tesseract as a comparison baseline** and for page-orientation detection.

1. Upload a scanned ledger page (PDF or image).
2. The page is auto-rotated and sent to the selected engine.
3. Rows return as structured JSON with confidence scores; low-confidence rows are flagged.
4. A reviewer corrects rows against the source image, then commits them to the catalog.

OCR runs on a local scanning station (it needs the API key and native libraries); the verified records sync to Supabase, which the web app serves to the whole school.

## Architecture

Three-tier, deployed on Vercel:

| Tier | Technology |
|------|------------|
| Frontend (SPA) | React 19, TypeScript, Vite, TanStack Query, React Router, i18next, Bootstrap 5 |
| Backend (REST API) | Flask 3, SQLAlchemy 2, Flask-Login |
| Database | Supabase (PostgreSQL) via psycopg3 |
| OCR | Anthropic Claude Vision API (primary) · Tesseract + Poppler (baseline) |

Role-based access is enforced in the Flask API (permission flags), not in the client.

## Run locally

**Backend** (Python 3.10+):

```bash
pip install -r requirements.txt
python scripts/run_local_sqlite.py      # serves the API on a local SQLite DB
```

**Frontend** (Node 18+):

```bash
cd frontend
npm install
npm run dev                             # http://localhost:5173
```

**OCR digitization** (optional — needs an Anthropic API key and the OCR extras):

```bash
pip install -r requirements-ocr.txt
# set ANTHROPIC_API_KEY in a .env file
```

## Project structure

```
app/         Flask backend — models, REST API blueprints, OCR services
frontend/    React + TypeScript SPA (Vite)
scripts/     local runners and data/maintenance scripts
api/         Vercel serverless entry point
```
