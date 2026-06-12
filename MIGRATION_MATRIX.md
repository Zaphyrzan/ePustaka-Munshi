# React Migration Matrix — every route accounted for

Generated from the live Flask route map (75 routes). Nothing is "migrated" until its
row is checked. Legend:

- **API-READY** — JSON endpoint already exists in `app/api/`
- **API-GAP** — JSON endpoint must be built before the React page
- **SERVER** — deliberately stays server-side (file generation, ops, local-only OCR processing)
- **CLIENT** — replaced by client-side behavior in React

## main

| Route | Plan | Status |
|---|---|---|
| `GET /` | React landing → redirect to dashboard/login | [ ] |
| `GET /dashboard` | React dashboard (stats via `/api/circulation/stats`; extend if needed) — API-READY | [ ] |
| `GET /health` | SERVER (ops endpoint) | [x] stays |
| `GET /pool-stats` | SERVER (ops endpoint) | [x] stays |
| `GET /set-language/<code>` | CLIENT (i18next) | [ ] |

## auth

| Route | Plan | Status |
|---|---|---|
| `GET,POST /auth/login` | React login — API-READY (`POST /api/auth/login`) | [ ] |
| `GET /auth/logout` | API-READY (`POST /api/auth/logout`) | [ ] |
| `GET,POST /auth/change-password` | API-READY | [ ] |
| `GET /auth/profile` | API-READY (`GET /api/auth/me`) | [ ] |
| `GET,POST /auth/profile/edit` | **API-GAP**: `PUT /api/auth/me` | [ ] |

## catalog

| Route | Plan | Status |
|---|---|---|
| `GET /catalog/` (+search) | React catalog list — API-READY (`GET /api/catalog/books`) | [ ] |
| `GET /catalog/book/<id>` | React book detail — API-READY (verify copies incl. barcode in payload) | [ ] |
| `GET,POST /catalog/book/add` | API-READY (`POST /api/catalog/books`) | [ ] |
| `GET,POST /catalog/book/<id>/edit` | API-READY (`PUT`) | [ ] |
| `POST /catalog/book/<id>/delete` | API-READY (`DELETE`) | [ ] |
| `GET,POST /catalog/book/<id>/copy/add` | **API-GAP**: `POST /api/catalog/books/<id>/copies` (must auto-generate accession+barcode like web route) | [ ] |
| `GET,POST /catalog/copy/<id>/edit` | **API-GAP**: `PUT /api/catalog/copies/<id>` (barcode read-only) | [ ] |
| `GET,POST /catalog/book/<id>/print-barcodes` | SERVER (print view) — link from React | [x] stays |
| `GET /catalog/api/barcode/<value>` | SERVER (PNG generation) — `<img>` src from React | [x] stays |
| `GET /catalog/api/copy/<barcode>` | scanner lookup, JSON already — reuse or port to api_catalog | [ ] |
| `GET /catalog/api/search` | superseded by `GET /api/catalog/books?search=` | [ ] verify+retire |

## circulation

| Route | Plan | Status |
|---|---|---|
| `GET /circulation/` | React circulation dashboard — API-READY (`/api/circulation/stats`) | [ ] |
| `GET,POST /circulation/checkout` | React checkout w/ scanner input — API-READY (`POST /api/circulation/checkout`) | [ ] |
| `GET,POST /circulation/return` | API-READY (`POST /api/circulation/return`) | [ ] |
| `POST /circulation/renew/<loan_id>` | API-READY (`POST /api/circulation/loans/<id>/renew`) | [ ] |
| `GET /circulation/active` | API-READY (`GET /api/circulation/loans?status=active`) — verify filter | [ ] |
| `GET /circulation/history` | API-READY (`GET /api/circulation/loans`) — verify filter | [ ] |
| `GET /circulation/overdue` | API-READY (`GET /api/circulation/overdue`) | [ ] |
| `GET /circulation/member/<id>/loans` | **API-GAP**: member loans endpoint (or `?member_id=` filter on loans) | [ ] |
| `POST /circulation/update-overdue` | **API-GAP**: `POST /api/circulation/update-overdue` | [ ] |
| `GET /circulation/api/member/<member_id>` | scanner/member lookup, JSON already — reuse or port | [ ] |
| `GET /circulation/api/copy/<barcode>/loan` | JSON already — reuse or port | [ ] |

## ocr — **entire JSON API must be built (`app/api/ocr_api.py`)**

OCR *processing* (vision API, Poppler, Tesseract) stays on the local Flask app by design —
Vercel has no binaries/API key. The React UI handles jobs/review/commit via API.

| Route | Plan | Status |
|---|---|---|
| `GET /ocr/` | **API-GAP**: `GET /api/ocr/jobs` (paginated) | [ ] |
| `GET /ocr/job/<id>` | **API-GAP**: `GET /api/ocr/jobs/<id>` (+results summary) | [ ] |
| `GET /ocr/job/<id>/review` | **API-GAP**: `GET /api/ocr/jobs/<id>/results` (paginated!) | [ ] |
| `POST /ocr/result/<id>/update` | **API-GAP**: `PUT /api/ocr/results/<id>` (fix is_valid handling like web) | [ ] |
| `POST /ocr/result/<id>/commit` | **API-GAP**: `POST /api/ocr/results/<id>/commit` (reuse `_commit_result_row`) | [ ] |
| `POST /ocr/job/<id>/bulk-review` | **API-GAP**: `POST /api/ocr/jobs/<id>/bulk-review` | [ ] |
| `POST /ocr/job/<id>/commit` | **API-GAP**: `POST /api/ocr/jobs/<id>/commit` (incremental semantics) | [ ] |
| `POST /ocr/job/<id>/delete` | **API-GAP**: `DELETE /api/ocr/jobs/<id>` | [ ] |
| `GET,POST /ocr/upload` | **API-GAP**: `POST /api/ocr/jobs` multipart (page cap enforced) — local Flask only | [ ] |
| `POST /ocr/job/<id>/process` | **API-GAP**: `POST /api/ocr/jobs/<id>/process` — local Flask only (SERVER on Vercel) | [ ] |
| `GET,POST /ocr/import-ledger` | Excel import — **API-GAP** or keep Flask page initially (decide in task 9) | [ ] |
| `GET /ocr/api/autocomplete` | JSON already — reuse | [ ] |
| `POST /ocr/api/suggest/book`, `/suggest/member` | JSON already — reuse | [ ] |

## student

| Route | Plan | Status |
|---|---|---|
| `GET /student/` | API-READY (`GET /api/student/dashboard`) | [ ] |
| `GET /student/search` | API-READY (`GET /api/student/search`) | [ ] |
| `GET /student/book/<id>` | API-READY (`GET /api/student/books/<id>`) | [ ] |
| `GET /student/my-loans` | API-READY (`GET /api/student/loans`) | [ ] |
| `GET /student/leaderboard` | API-READY (`GET /api/student/leaderboard`) | [ ] |
| `GET /student/api/book-availability/<id>` | fold into student book detail payload | [ ] |

## users (admin) — largest module, most API gaps

| Route | Plan | Status |
|---|---|---|
| `GET /users/members` | API-READY (`GET /api/users/members`) | [ ] |
| `GET /users/members/<id>` | API-READY (`GET /api/users/members/<id>`) | [ ] |
| `GET,POST /users/members/add` | API-READY (`POST /api/users/members`) | [ ] |
| `GET,POST /users/members/<id>/edit` | API-READY (`PUT /api/users/members/<id>`) | [ ] |
| `POST /users/members/<id>/delete` (+confirm page) | **API-GAP**: `DELETE /api/users/members/<id>` | [ ] |
| `POST /users/members/<id>/promote-staff` | **API-GAP**: `POST /api/users/members/<id>/promote` | [ ] |
| `POST /users/members/<id>/demote-staff` | **API-GAP**: `POST /api/users/members/<id>/demote` | [ ] |
| `GET /users/staff` | API-READY (`GET /api/users/staff`) | [ ] |
| `GET /users/staff/<id>` | API-READY | [ ] |
| `GET,POST /users/staff/add` | API-READY (`POST /api/users/staff`) | [ ] |
| `GET,POST /users/staff/<id>/edit` | API-READY (`PUT`) | [ ] |
| `POST /users/staff/<id>/delete` | **API-GAP**: `DELETE /api/users/staff/<id>` | [ ] |
| `GET,POST /users/staff/import` | **API-GAP**: multipart import endpoint (or keep Flask page initially) | [ ] |
| `GET,POST /users/students/import` | **API-GAP**: multipart import endpoint (or keep Flask page initially) | [ ] |
| `GET /users/students/active` | **API-GAP**: filtered member list (`?status=active&type=Student`) | [ ] |
| `GET /users/students/graduation-list` | **API-GAP**: graduation list endpoint | [ ] |
| `GET,POST /users/admin/promote-students` | **API-GAP**: bulk form-level promotion endpoint | [ ] |
| `POST /users/students/<id>/delete` | **API-GAP** (see member delete) | [ ] |
| `POST /users/students/<id>/mark-for-deletion` / `unmark` | **API-GAP**: mark/unmark endpoints | [ ] |
| `GET /users/api/class-groups`, `/api/form-levels` | JSON already — reuse | [ ] |

## Post-migration (explicitly deferred, user-approved)

- Staff vs Member disambiguation (see memory: staff-vs-member-confusion) — UI naming
  split "Staff Accounts" vs "Library Members", member_type 'Staff' → 'Teacher'.
