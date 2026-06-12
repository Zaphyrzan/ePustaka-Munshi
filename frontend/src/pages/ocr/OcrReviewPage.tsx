import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap, type Paginated } from '../../api/client'
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

/** The OCR validation interface: review, correct and upload extracted ledger rows */
export default function OcrReviewPage() {
  const { jobId } = useParams()
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [drafts, setDrafts] = useState<Drafts>({})
  const [msg, setMsg] = useState<{ kind: 'success' | 'danger'; text: string } | null>(null)

  const { data: job } = useQuery({
    queryKey: ['ocr-job', jobId],
    queryFn: () => unwrap<OcrJob>(api.get(`/api/ocr/jobs/${jobId}`)),
  })

  const { data, isLoading } = useQuery({
    queryKey: ['ocr-results', jobId, page, statusFilter],
    queryFn: () =>
      unwrap<Paginated<OcrRow>>(
        api.get(`/api/ocr/jobs/${jobId}/results`, {
          params: { page, per_page: 50, ...(statusFilter && { status: statusFilter }) },
        }),
      ),
    placeholderData: keepPreviousData,
  })

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
      refresh()
    },
    onError: (err) => setMsg({ kind: 'danger', text: err instanceof Error ? err.message : t('error') }),
  })

  const uploadRow = useMutation({
    mutationFn: (row: OcrRow) => unwrap(api.post(`/api/ocr/results/${row.id}/commit`, rowPayload(row))),
    onSuccess: (_d, row) => {
      setMsg({ kind: 'success', text: `Row ${row.row_number} uploaded to catalog` })
      setDrafts((d) => ({ ...d, [row.id]: {} }))
      refresh()
    },
    onError: (err) => setMsg({ kind: 'danger', text: err instanceof Error ? err.message : t('error') }),
  })

  const bulkReview = useMutation({
    mutationFn: () => unwrap(api.post(`/api/ocr/jobs/${jobId}/bulk-review`)),
    onSuccess: () => {
      setMsg({ kind: 'success', text: 'All rows marked reviewed — ready to upload' })
      refresh()
    },
  })

  const commitBatch = useMutation({
    mutationFn: () =>
      unwrap<{ committed: number; remaining: number; errors: string[] }>(
        api.post(`/api/ocr/jobs/${jobId}/commit`, {}, { timeout: 300_000 }),
      ),
    onSuccess: (d) => {
      setMsg({
        kind: 'success',
        text: `Uploaded ${d.committed} books` + (d.errors.length ? ` (${d.errors.length} rows had issues)` : ''),
      })
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

  const pg = data?.pagination

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
            {job?.result_count ?? '—'} rows • {job?.reviewed_count ?? '—'} reviewed • {job?.committed_count ?? '—'}{' '}
            uploaded
          </small>
        </div>
        <div className="d-flex gap-2">
          <button
            className="btn btn-outline-primary"
            onClick={() => {
              if (confirm('Mark every unreviewed row as reviewed and valid?')) bulkReview.mutate()
            }}
            disabled={bulkReview.isPending}
          >
            <i className="bi bi-check2-all me-1" />
            Mark all reviewed
          </button>
          <button
            className="btn btn-success"
            onClick={() => commitBatch.mutate()}
            disabled={commitBatch.isPending || (job?.ready_to_commit ?? 0) === 0}
          >
            <i className="bi bi-cloud-upload me-1" />
            {commitBatch.isPending ? 'Uploading…' : `Upload ${job?.ready_to_commit ?? 0} reviewed`}
          </button>
        </div>
      </div>

      {msg && <div className={`alert alert-${msg.kind} py-2`}>{msg.text}</div>}

      <ul className="nav nav-pills mb-3">
        {[
          ['', 'All'],
          ['pending', 'Pending'],
          ['reviewed', 'Reviewed'],
          ['committed', 'Uploaded'],
        ].map(([value, label]) => (
          <li className="nav-item" key={value}>
            <button
              className={`nav-link py-1 ${statusFilter === value ? 'active' : ''}`}
              onClick={() => {
                setStatusFilter(value)
                setPage(1)
              }}
            >
              {label}
            </button>
          </li>
        ))}
      </ul>

      {isLoading ? (
        <div className="text-muted py-5 text-center">{t('loading')}</div>
      ) : (
        <div className="card shadow-sm table-responsive">
          <table className="table table-sm table-hover mb-0 align-middle" style={{ fontSize: '0.85rem' }}>
            <thead className="table-light">
              <tr>
                <th style={{ width: 60 }}>Pg/Row</th>
                <th style={{ width: 90 }}>Perolehan</th>
                <th style={{ width: 90 }}>Panggilan</th>
                <th>Pengarang</th>
                <th style={{ minWidth: 180 }}>Tajuk Buku</th>
                <th>Penerbit</th>
                <th style={{ width: 70 }}>Tahun</th>
                <th style={{ width: 80 }}>Punca</th>
                <th style={{ width: 55 }}>Conf</th>
                <th style={{ width: 190 }} className="text-end">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((row) => {
                const rowClass = row.committed
                  ? 'table-secondary'
                  : row.is_reviewed
                    ? 'table-success'
                    : (row.confidence_overall ?? 1) < 0.7
                      ? 'table-warning'
                      : ''
                return (
                  <tr key={row.id} className={rowClass}>
                    <td className="text-muted">
                      {row.page_number}/{row.row_number}
                    </td>
                    {EDIT_FIELDS.map((f) => (
                      <td key={f}>
                        <input
                          className="form-control form-control-sm"
                          value={fieldValue(row, f)}
                          onChange={(e) => edit(row, f, e.target.value)}
                          disabled={row.committed}
                        />
                      </td>
                    ))}
                    <td className="text-center text-muted">
                      {row.confidence_overall != null ? `${Math.round(row.confidence_overall * 100)}%` : '—'}
                    </td>
                    <td className="text-end text-nowrap">
                      {row.committed ? (
                        <span className="badge bg-success">
                          <i className="bi bi-cloud-check me-1" />
                          Uploaded
                        </span>
                      ) : (
                        <>
                          <button
                            className="btn btn-primary btn-sm me-1"
                            onClick={() => saveRow.mutate(row)}
                            disabled={saveRow.isPending}
                          >
                            Save
                          </button>
                          <button
                            className="btn btn-success btn-sm"
                            onClick={() => uploadRow.mutate(row)}
                            disabled={uploadRow.isPending}
                          >
                            Save & Upload
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                )
              })}
              {data?.items.length === 0 && (
                <tr>
                  <td colSpan={10} className="text-center text-muted py-4">
                    No rows
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {pg && pg.total_pages > 1 && (
        <nav className="d-flex justify-content-center mt-3 gap-2 align-items-center">
          <button className="btn btn-outline-primary btn-sm" disabled={!pg.has_prev} onClick={() => setPage(page - 1)}>
            ‹
          </button>
          <span className="small text-muted">
            {pg.page} / {pg.total_pages} ({pg.total} rows)
          </span>
          <button className="btn btn-outline-primary btn-sm" disabled={!pg.has_next} onClick={() => setPage(page + 1)}>
            ›
          </button>
        </nav>
      )}
    </div>
  )
}
