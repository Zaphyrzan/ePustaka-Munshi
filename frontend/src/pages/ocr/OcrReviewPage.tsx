import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { API_BASE, api, unwrap, type Paginated } from '../../api/client'
import type { OcrJob } from './OcrJobsPage'

interface OcrRow {
  id: number
  page_number: number
  row_number: number
  no_perolehan: string | null
  no_panggilan: string | null
  pengarang: string | null
  tajuk_buku: string | null
  penerbit: string | null
  tarikh_penerbit: string | null
  punca: string | null
  confidence_overall: number | null
  is_reviewed: boolean
  is_valid: boolean
  committed: boolean
}

const EDIT_FIELDS = ['no_perolehan', 'no_panggilan', 'pengarang', 'tajuk_buku', 'penerbit', 'tarikh_penerbit', 'punca'] as const
type EditField = (typeof EDIT_FIELDS)[number]
type Drafts = Record<number, Partial<Record<EditField, string>>>

const FIELD_LABEL: Record<EditField, string> = {
  no_perolehan: 'Perolehan',
  no_panggilan: 'Panggilan',
  pengarang: 'Pengarang',
  tajuk_buku: 'Tajuk Buku',
  penerbit: 'Penerbit',
  tarikh_penerbit: 'Tahun',
  punca: 'Punca',
}

/** Colour band for a confidence score (red < 60%, amber 60–85%, green ≥ 85%). */
function confColor(c: number | null): string {
  if (c == null) return 'secondary'
  if (c >= 0.85) return 'success'
  if (c >= 0.6) return 'warning'
  return 'danger'
}

/** OCR validation interface: verify extracted rows against the scanned page. */
export default function OcrReviewPage() {
  const { jobId } = useParams()
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [ledgerPage, setLedgerPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [lowConfOnly, setLowConfOnly] = useState(false)
  const [sortByConf, setSortByConf] = useState(false)
  const [showImage, setShowImage] = useState(true)
  const [imgError, setImgError] = useState(false)
  const [editRow, setEditRow] = useState<number | null>(null)
  const [drafts, setDrafts] = useState<Drafts>({})
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [rowPage, setRowPage] = useState(1)
  const [perPage, setPerPage] = useState(25)
  const [msg, setMsg] = useState<{ kind: 'success' | 'danger'; text: string } | null>(null)

  const { data: job } = useQuery({
    queryKey: ['ocr-job', jobId],
    queryFn: () => unwrap<OcrJob>(api.get(`/api/ocr/jobs/${jobId}`)),
  })
  const pageCount = job?.page_count || 1

  const { data, isLoading } = useQuery({
    queryKey: ['ocr-results', jobId, ledgerPage, statusFilter],
    queryFn: () =>
      unwrap<Paginated<OcrRow>>(
        api.get(`/api/ocr/jobs/${jobId}/results`, {
          params: { page: 1, per_page: 200, page_number: ledgerPage, ...(statusFilter && { status: statusFilter }) },
        }),
      ),
  })

  useEffect(() => {
    setImgError(false)
    setSelected(new Set())
    setEditRow(null)
  }, [ledgerPage])

  // Back to the first chunk whenever the visible set changes.
  useEffect(() => {
    setRowPage(1)
  }, [ledgerPage, statusFilter, lowConfOnly, sortByConf, perPage])

  function refresh() {
    queryClient.invalidateQueries({ queryKey: ['ocr-results', jobId] })
    queryClient.invalidateQueries({ queryKey: ['ocr-job', jobId] })
  }
  function rowPayload(row: OcrRow) {
    return { ...drafts[row.id], is_valid: true }
  }

  const saveRow = useMutation({
    mutationFn: (row: OcrRow) => unwrap(api.put(`/api/ocr/results/${row.id}`, rowPayload(row))),
    onSuccess: (_d, row) => {
      setDrafts((d) => ({ ...d, [row.id]: {} }))
      setEditRow(null)
      refresh()
    },
    onError: (err) => setMsg({ kind: 'danger', text: err instanceof Error ? err.message : t('error') }),
  })

  const uploadRow = useMutation({
    mutationFn: (row: OcrRow) => unwrap(api.post(`/api/ocr/results/${row.id}/commit`, rowPayload(row))),
    onSuccess: (_d, row) => {
      setMsg({ kind: 'success', text: `Row ${row.row_number} uploaded to catalog` })
      setDrafts((d) => ({ ...d, [row.id]: {} }))
      setEditRow(null)
      refresh()
    },
    onError: (err) => setMsg({ kind: 'danger', text: err instanceof Error ? err.message : t('error') }),
  })

  const reviewSelected = useMutation({
    mutationFn: (ids: number[]) => unwrap(api.post(`/api/ocr/jobs/${jobId}/review-selected`, { ids })),
    onSuccess: (_d, ids) => {
      setMsg({ kind: 'success', text: `Marked ${ids.length} row(s) reviewed` })
      setSelected(new Set())
      refresh()
    },
    onError: (err) => setMsg({ kind: 'danger', text: err instanceof Error ? err.message : t('error') }),
  })

  const commitSelected = useMutation({
    mutationFn: (ids: number[]) =>
      unwrap<{ committed: number; errors: string[] }>(
        api.post(`/api/ocr/jobs/${jobId}/commit-selected`, { ids }, { timeout: 120_000 }),
      ),
    onSuccess: (d) => {
      setMsg({
        kind: 'success',
        text: `Uploaded ${d.committed} books` + (d.errors.length ? ` (${d.errors.length} had issues)` : ''),
      })
      setSelected(new Set())
      refresh()
    },
    onError: (err) => setMsg({ kind: 'danger', text: err instanceof Error ? err.message : t('error') }),
  })

  function edit(row: OcrRow, field: EditField, value: string) {
    setDrafts((d) => ({ ...d, [row.id]: { ...d[row.id], [field]: value } }))
  }
  function fieldValue(row: OcrRow, field: EditField) {
    return drafts[row.id]?.[field] ?? row[field] ?? ''
  }
  function toggleSelect(id: number) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // Client-side confidence filter/sort over the current ledger page's rows,
  // then slice into pages of `perPage` so reviewers work in small chunks.
  let processed = data?.items ?? []
  if (lowConfOnly) processed = processed.filter((r) => (r.confidence_overall ?? 1) < 0.7)
  if (sortByConf) processed = [...processed].sort((a, b) => (a.confidence_overall ?? 1) - (b.confidence_overall ?? 1))
  const totalRows = processed.length
  const totalRowPages = Math.max(1, Math.ceil(totalRows / perPage))
  const start = (rowPage - 1) * perPage
  const rows = processed.slice(start, start + perPage)
  // Header checkbox selects the uncommitted rows on the current chunk.
  const selectableIds = rows.filter((r) => !r.committed).map((r) => r.id)
  const allSelected = selectableIds.length > 0 && selectableIds.every((id) => selected.has(id))

  return (
    <div>
      <nav className="mb-2">
        <Link to="/ocr" className="text-decoration-none">
          ‹ {t('ocr')}
        </Link>
      </nav>
      <div className="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
        <div>
          <h4 className="mb-0">{job?.job_name || `Job ${jobId}`}</h4>
          <small className="text-muted">
            {job?.result_count ?? '—'} {t('rows').toLowerCase()} • {job?.reviewed_count ?? '—'}{' '}
            {t('reviewed').toLowerCase()} • {job?.committed_count ?? '—'} {t('uploaded').toLowerCase()}
          </small>
        </div>
      </div>

      {msg && <div className={`alert alert-${msg.kind} py-2`}>{msg.text}</div>}

      {/* Controls */}
      <div className="d-flex flex-wrap gap-2 align-items-center mb-3">
        <div className="btn-group btn-group-sm">
          <button
            className="btn btn-outline-secondary"
            disabled={ledgerPage <= 1}
            onClick={() => setLedgerPage((p) => Math.max(1, p - 1))}
          >
            ‹
          </button>
          <span className="btn btn-light disabled">
            Page {ledgerPage} / {pageCount}
          </span>
          <button
            className="btn btn-outline-secondary"
            disabled={ledgerPage >= pageCount}
            onClick={() => setLedgerPage((p) => Math.min(pageCount, p + 1))}
          >
            ›
          </button>
        </div>

        <ul className="nav nav-pills">
          {[
            ['', 'All'],
            ['pending', 'Pending'],
            ['reviewed', t('reviewed')],
            ['committed', t('uploaded')],
          ].map(([value, label]) => (
            <li className="nav-item" key={value}>
              <button
                className={`nav-link py-1 ${statusFilter === value ? 'active' : ''}`}
                onClick={() => setStatusFilter(value)}
              >
                {label}
              </button>
            </li>
          ))}
        </ul>

        <div className="form-check ms-2">
          <input
            id="lowconf"
            type="checkbox"
            className="form-check-input"
            checked={lowConfOnly}
            onChange={(e) => setLowConfOnly(e.target.checked)}
          />
          <label htmlFor="lowconf" className="form-check-label small">
            Low confidence only
          </label>
        </div>
        <div className="form-check">
          <input
            id="sortconf"
            type="checkbox"
            className="form-check-input"
            checked={sortByConf}
            onChange={(e) => setSortByConf(e.target.checked)}
          />
          <label htmlFor="sortconf" className="form-check-label small">
            Lowest confidence first
          </label>
        </div>
        <button className="btn btn-sm btn-outline-secondary ms-auto" onClick={() => setShowImage((v) => !v)}>
          <i className={`bi bi-image me-1`} />
          {showImage ? 'Hide scan' : 'Show scan'}
        </button>
      </div>

      {/* Source scan for this page */}
      {showImage && (
        <div className="card shadow-sm mb-3">
          <div className="card-header bg-white py-2 small text-muted">
            <i className="bi bi-card-image me-1" />
            Scanned source — page {ledgerPage}
          </div>
          <div className="card-body text-center p-2" style={{ maxHeight: 360, overflow: 'auto' }}>
            {imgError ? (
              <div className="text-muted small py-4">
                <i className="bi bi-exclamation-circle me-1" />
                Source scan is only viewable on the local scanning station.
              </div>
            ) : (
              <img
                src={`${API_BASE}/api/ocr/jobs/${jobId}/page/${ledgerPage}`}
                alt={`Scanned page ${ledgerPage}`}
                style={{ maxWidth: '100%' }}
                onError={() => setImgError(true)}
              />
            )}
          </div>
        </div>
      )}

      {/* Selection toolbar */}
      {selected.size > 0 && (
        <div className="alert alert-primary d-flex align-items-center gap-2 py-2">
          <span className="me-auto">
            <strong>{selected.size}</strong> selected
          </span>
          <button
            className="btn btn-outline-primary btn-sm"
            disabled={reviewSelected.isPending}
            onClick={() => reviewSelected.mutate([...selected])}
          >
            <i className="bi bi-check2-all me-1" />
            Mark reviewed
          </button>
          <button
            className="btn btn-success btn-sm"
            disabled={commitSelected.isPending}
            onClick={() => {
              if (confirm(`Upload ${selected.size} selected row(s) to the catalog?`)) commitSelected.mutate([...selected])
            }}
          >
            <i className="bi bi-cloud-upload me-1" />
            {commitSelected.isPending ? 'Uploading…' : 'Upload selected'}
          </button>
          <button className="btn btn-outline-secondary btn-sm" onClick={() => setSelected(new Set())}>
            {t('clear')}
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="text-muted py-5 text-center">{t('loading')}</div>
      ) : (
        <div className="card shadow-sm table-responsive">
          <table className="table table-sm table-hover mb-0 align-middle" style={{ fontSize: '0.85rem' }}>
            <thead className="table-light">
              <tr>
                <th style={{ width: 34 }}>
                  <input
                    type="checkbox"
                    className="form-check-input"
                    checked={allSelected}
                    disabled={selectableIds.length === 0}
                    onChange={() => setSelected(allSelected ? new Set() : new Set(selectableIds))}
                  />
                </th>
                <th style={{ width: 48 }}>Row</th>
                {EDIT_FIELDS.map((f) => (
                  <th key={f}>{FIELD_LABEL[f]}</th>
                ))}
                <th style={{ width: 60 }} className="text-center">
                  Conf
                </th>
                <th style={{ width: 150 }} className="text-end">
                  {t('actions')}
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const editing = editRow === row.id
                const conf = confColor(row.confidence_overall)
                return (
                  <tr
                    key={row.id}
                    className={row.committed ? 'table-light text-muted' : ''}
                    style={{ borderLeft: `3px solid var(--bs-${conf})` }}
                  >
                    <td>
                      {!row.committed && (
                        <input
                          type="checkbox"
                          className="form-check-input"
                          checked={selected.has(row.id)}
                          onChange={() => toggleSelect(row.id)}
                        />
                      )}
                    </td>
                    <td className="text-muted">{row.row_number}</td>
                    {EDIT_FIELDS.map((f) => (
                      <td key={f}>
                        {editing ? (
                          <input
                            className="form-control form-control-sm"
                            value={fieldValue(row, f)}
                            onChange={(e) => edit(row, f, e.target.value)}
                          />
                        ) : (
                          <span className={row[f] ? '' : 'text-muted'}>{row[f] || '—'}</span>
                        )}
                      </td>
                    ))}
                    <td className="text-center">
                      <span className={`badge bg-${conf}${conf === 'warning' ? ' text-dark' : ''}`}>
                        {row.confidence_overall != null ? `${Math.round(row.confidence_overall * 100)}%` : '—'}
                      </span>
                    </td>
                    <td className="text-end text-nowrap">
                      {row.committed ? (
                        <span className="badge bg-success">
                          <i className="bi bi-cloud-check me-1" />
                          {t('uploaded')}
                        </span>
                      ) : editing ? (
                        <>
                          <button
                            className="btn btn-primary btn-sm me-1"
                            onClick={() => saveRow.mutate(row)}
                            disabled={saveRow.isPending}
                          >
                            {t('save')}
                          </button>
                          <button
                            className="btn btn-success btn-sm me-1"
                            onClick={() => uploadRow.mutate(row)}
                            disabled={uploadRow.isPending}
                            title="Save & upload this row"
                          >
                            <i className="bi bi-cloud-upload" />
                          </button>
                          <button className="btn btn-outline-secondary btn-sm" onClick={() => setEditRow(null)}>
                            {t('cancel')}
                          </button>
                        </>
                      ) : (
                        <>
                          {row.is_reviewed && (
                            <span className="badge bg-info text-dark me-1" title="Reviewed">
                              <i className="bi bi-check2" />
                            </span>
                          )}
                          <button className="btn btn-outline-primary btn-sm" onClick={() => setEditRow(row.id)}>
                            <i className="bi bi-pencil" />
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                )
              })}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={11} className="text-center text-muted py-4">
                    No rows on this page
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Row pagination + page size */}
      {totalRows > 0 && (
        <div className="d-flex flex-wrap justify-content-between align-items-center mt-3 gap-2">
          <div className="d-flex align-items-center gap-2 small text-muted">
            <span>Show</span>
            <select
              className="form-select form-select-sm"
              style={{ width: 'auto' }}
              value={perPage}
              onChange={(e) => setPerPage(Number(e.target.value))}
            >
              {[10, 25, 50, 100].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
            <span>
              per page — showing {start + 1}–{Math.min(start + perPage, totalRows)} of {totalRows}
            </span>
          </div>
          {totalRowPages > 1 && (
            <nav className="d-flex gap-2 align-items-center">
              <button
                className="btn btn-outline-primary btn-sm"
                disabled={rowPage <= 1}
                onClick={() => setRowPage((p) => Math.max(1, p - 1))}
              >
                ‹
              </button>
              <span className="small text-muted">
                {rowPage} / {totalRowPages}
              </span>
              <button
                className="btn btn-outline-primary btn-sm"
                disabled={rowPage >= totalRowPages}
                onClick={() => setRowPage((p) => Math.min(totalRowPages, p + 1))}
              >
                ›
              </button>
            </nav>
          )}
        </div>
      )}
    </div>
  )
}
