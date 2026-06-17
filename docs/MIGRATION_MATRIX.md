# React Migration Matrix — every route accounted for

Updated after the migration build (branch `react-app`). Legend:
- ✅ migrated to React (verified against live API)
- 🏠 deliberately stays server-side (file generation, ops, local-only OCR processing)
- 🔗 available via classic Flask page, linked from the React UI (rare admin tasks)

## main
| Route | Status |
|---|---|
| `GET /` | ✅ React redirect → dashboard/login |
| `GET /dashboard` | ✅ React dashboard (loan stats + book totals) |
| `GET /health`, `GET /pool-stats` | 🏠 ops endpoints |
| `GET /set-language/<code>` | ✅ client-side i18next EN/BM toggle |

## auth
| Route | Status |
|---|---|
| login / logout / change-password | ✅ verified live (session cookie flow) |
| profile view | ✅ (header shows current user; data via /api/auth/me) |
| profile edit | 🔗 Flask page (PUT /api/auth/me not yet built — post-symposium) |

## catalog
| Route | Status |
|---|---|
| browse + search + pagination | ✅ verified live |
| book detail with copies + barcode images | ✅ verified live (barcode PNGs served by Flask 🏠) |
| add / edit / delete book | ✅ |
| add copy (auto accession + barcode) | ✅ verified live via new POST /api/catalog/books/<id>/copies |
| edit copy | API ✅ (PUT /api/catalog/copies/<id>); UI 🔗 Flask page |
| print barcodes | 🏠 Flask print view, linked from React book detail |
| scanner copy lookup | ✅ reused by circulation pages |

## circulation
| Route | Status |
|---|---|
| checkout (scanner-first: member → barcode) | ✅ verified live full cycle |
| return (barcode → confirm) | ✅ verified live |
| renew | ✅ |
| active / overdue / history lists | ✅ (tabs) |
| member loans | ✅ via loans?member_id= filter (API already supported it) |
| update-overdue maintenance action | 🔗 Flask (cron-style admin action) |

## ocr — **new JSON API built: app/api/ocr_api.py (10 endpoints)**
| Route | Status |
|---|---|
| job list + status/progress counts | ✅ verified live |
| upload (page cap enforced) | ✅ API + React form (local Flask only 🏠 for processing) |
| process job (vision/tesseract) | ✅ API; returns 503 on Vercel (no key/binaries) by design |
| review table (validation interface) | ✅ verified live — inline edit, paginated 50/page |
| save row / save & upload row | ✅ verified live (Uploaded badge + counters) |
| mark all reviewed | ✅ |
| incremental batch commit | ✅ verified (36 committed, dupes rejected) |
| delete job | ✅ |
| Excel ledger import | 🔗 Flask page |
| autocomplete/suggest helpers | ✅ reusable as-is (JSON already) |

## student
| Route | Status |
|---|---|
| portal: my loans / search / NILAM leaderboard | ✅ verified with STU0001 login (payload shapes adapted) |
| book availability | ✅ folded into search/detail data |

## users (admin)
| Route | Status |
|---|---|
| members list/search/add/edit | ✅ |
| staff list/add/edit | ✅ |
| delete member (active-loan guard) / delete staff (self-guard) | ✅ new DELETE endpoints |
| promote to / demote from Student Assistant | ✅ new endpoints mirroring web logic |
| Excel imports (students/staff) | 🔗 Flask pages, linked from React |
| graduation list / promote-students / mark-for-deletion | 🔗 Flask pages (yearly admin tasks) |
| class-groups / form-levels helpers | ✅ JSON already |

## Deployment
- Flask API: unchanged on Vercel (epustaka-munshi). Flask UI remains live = fallback.
- React app: `frontend/` → separate Vercel project (static). `vercel.json` SPA rewrite
  included. CORS already whitelists epustaka-react.vercel.app.
- Local dev: `scripts/run_local_sqlite.py` (Flask, SQLite-pinned) + `npm run dev` in frontend/.

## Post-migration backlog (user-approved deferrals)
1. Staff vs Member disambiguation (memory: staff-vs-member-confusion) — naming split
   started in React Users tabs; rename member_type 'Staff' → 'Teacher' pending.
2. Change production admin password (admin/admin123 currently works on prod!).
3. PUT /api/auth/me (profile edit), React copy-edit UI, API-based Excel imports.
