import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap, API_BASE, type Paginated } from '../../api/client'
import type { OcrJob } from './OcrJobsPage'

const STATUS_BADGE: Record<string, string> = {
  pending: 'bg-secondary',
  processing: 'bg-primary',
  completed: 'bg-success',
  reviewed: 'bg-info text-dark',
  committed: 'bg-dark',
  failed: 'bg-danger',
}

interface RecordRow {
  id: number
  row_number: number
  no_perolehan: string | null
  tajuk_buku: string | null
  pengarang: string | null
  penerbit: string | null
  confidence_overall: number | null
  is_reviewed: boolean
  is_valid: boolean
  committed: boolean
}

function confColor(c: number | null): string {
  if (c == null) return 'secondary'
  if (c >= 0.85) return 'success'
  if (c >= 0.6) return 'warning'
  return 'danger'
}
function fmt(iso?: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Read-only overview of an OCR job (the "inspect before you edit" view). */
export default function OcrJobDetailPage() {
  const { jobId } = useParams()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [engine, setEngine] = useState<'vision' | 'tesseract'>('vision')
  const [imgError, setImgError] = useState(false)
  const [msg, setMsg] = useState<{ kind: 'success' | 'danger'; text: string } | null>(null)

  const { data: job } = useQuery({
    queryKey: ['ocr-job', jobId],
    queryFn: () => unwrap<OcrJob>(api.get(`/api/ocr/jobs/${jobId}`)),
  })

  const process = useMutation({
    mutationFn: () =>
      unwrap(api.post(`/api/ocr/jobs/${jobId}/process`, { engine }, { timeout: 600_000 })),
    onSuccess: () => {
      setMsg({ kind: 'success', text: t('ocrReviewResults') })
      queryClient.invalidateQueries({ queryKey: ['ocr-job', jobId] })
      queryClient.invalidateQueries({ queryKey: ['ocr-results', jobId] })
      queryClient.invalidateQueries({ queryKey: ['ocr-jobs'] })
    },
    onError: (err) => setMsg({ kind: 'danger', text: err instanceof Error ? err.message : t('error') }),
  })

  const isPending = job?.status === 'pending' || job?.status === 'failed'

  const { data, isLoading } = useQuery({
    queryKey: ['ocr-results', jobId, page, ''],
    queryFn: () =>
      unwrap<Paginated<RecordRow>>(api.get(`/api/ocr/jobs/${jobId}/results`, { params: { page, per_page: 25 } })),
    placeholderData: keepPreviousData,
  })

  const deleteJob = useMutation({
    mutationFn: () => unwrap(api.delete(`/api/ocr/jobs/${jobId}`)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ocr-jobs'] })
      navigate('/ocr')
    },
  })

  const total = job?.result_count ?? 0
  const reviewed = job?.reviewed_count ?? 0
  const pending = Math.max(0, total - reviewed)
  const pg = data?.pagination

  return (
    <div>
      <h4 className="mb-3">{t('ocrJobDetails')}</h4>
      <div className="row g-4">
        <div className="col-lg-8">
          {msg && <div className={`alert alert-${msg.kind} py-2`}>{msg.text}</div>}

          {/* Source scan preview — inspect the page before processing it */}
          <div className="card shadow-sm mb-4">
            <div className="card-header bg-white d-flex justify-content-between align-items-center flex-wrap gap-2">
              <h6 className="mb-0">
                <i className="bi bi-card-image me-2" />
                {t('ocrSourceScan')}
              </h6>
              {isPending && (
                <div className="d-flex gap-2 align-items-center">
                  <select
                    className="form-select form-select-sm"
                    style={{ width: 'auto' }}
                    value={engine}
                    onChange={(e) => setEngine(e.target.value as 'vision' | 'tesseract')}
                  >
                    <option value="vision">Claude Vision (AI)</option>
                    <option value="tesseract">Tesseract (baseline)</option>
                  </select>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => {
                      setMsg(null)
                      process.mutate()
                    }}
                    disabled={process.isPending}
                  >
                    <i className="bi bi-cpu me-1" />
                    {process.isPending ? 'Processing…' : t('processNow')}
                  </button>
                </div>
              )}
            </div>
            <div className="card-body text-center p-2" style={{ maxHeight: 480, overflow: 'auto' }}>
              {isPending && <p className="small text-muted mb-2">{t('ocrPreviewHint')}</p>}
              {imgError ? (
                <div className="text-muted small py-4">
                  <i className="bi bi-exclamation-circle me-1" />
                  {t('ocrScanLocalOnly')}
                </div>
              ) : (
                <img
                  src={`${API_BASE}/api/ocr/jobs/${jobId}/page/1`}
                  alt="Scanned source page 1"
                  className="img-fluid border rounded"
                  onError={() => setImgError(true)}
                />
              )}
            </div>
          </div>

          {/* Job info */}
          <div className="card shadow-sm mb-4">
            <div className="card-body">
              <div className="d-flex justify-content-between align-items-start mb-3">
                <h5 className="mb-0">{job?.job_name || `Job ${jobId}`}</h5>
                <span className={`badge text-uppercase ${STATUS_BADGE[job?.status || ''] || 'bg-secondary'}`}>
                  {job?.status || '—'}
                </span>
              </div>
              <table className="table table-sm mb-3">
                <tbody>
                  <tr>
                    <th className="fw-semibold" style={{ width: 160 }}>
                      {t('ocrSourceFile')}
                    </th>
                    <td>{job?.original_filename || '—'}</td>
                  </tr>
                  <tr>
                    <th className="fw-semibold">{t('ocrSourceType')}</th>
                    <td>{job?.source_type || '—'}</td>
                  </tr>
                  <tr>
                    <th className="fw-semibold">{t('ocrPages')}</th>
                    <td>{job?.page_count ?? '—'}</td>
                  </tr>
                  <tr>
                    <th className="fw-semibold">{t('ocrCreated')}</th>
                    <td>{fmt(job?.created_at)}</td>
                  </tr>
                  <tr>
                    <th className="fw-semibold">{t('ocrCompleted')}</th>
                    <td>{fmt(job?.completed_at)}</td>
                  </tr>
                </tbody>
              </table>
              <div className="d-flex gap-2">
                <Link to={`/ocr/${jobId}/review`} className="btn btn-success">
                  <i className="bi bi-check2-square me-1" />
                  {t('ocrReviewResults')}
                </Link>
                <button
                  className="btn btn-outline-danger"
                  onClick={() => {
                    if (confirm(`Delete job "${job?.job_name}"?`)) deleteJob.mutate()
                  }}
                >
                  <i className="bi bi-trash me-1" />
                  {t('delete')}
                </button>
              </div>
            </div>
          </div>

          {/* Extracted records */}
          <div className="card shadow-sm">
            <div className="card-header bg-white">
              <h6 className="mb-0">
                {t('ocrExtractedRecords')} ({total})
              </h6>
            </div>
            {isLoading ? (
              <div className="text-muted py-5 text-center">{t('loading')}</div>
            ) : (
              <div className="table-responsive">
                <table className="table table-hover mb-0 align-middle" style={{ fontSize: '0.88rem' }}>
                  <thead className="table-light">
                    <tr>
                      <th style={{ width: 40 }}>#</th>
                      <th>{t('accessionNo')}</th>
                      <th>{t('title')}</th>
                      <th>{t('author')}</th>
                      <th>{t('publisher')}</th>
                      <th className="text-center">Conf</th>
                      <th>{t('status')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data?.items.map((r) => {
                      const conf = confColor(r.confidence_overall)
                      const status = r.committed
                        ? { label: t('uploaded'), cls: 'bg-success' }
                        : r.is_reviewed && r.is_valid
                          ? { label: t('ocrValid'), cls: 'bg-success' }
                          : { label: 'Pending', cls: 'bg-warning text-dark' }
                      return (
                        <tr key={r.id}>
                          <td className="text-muted">{r.row_number}</td>
                          <td className="fw-semibold">{r.no_perolehan || '—'}</td>
                          <td>{r.tajuk_buku || '—'}</td>
                          <td>{r.pengarang || '—'}</td>
                          <td>{r.penerbit || '—'}</td>
                          <td className="text-center">
                            <span className={`badge bg-${conf}${conf === 'warning' ? ' text-dark' : ''}`}>
                              {r.confidence_overall != null ? `${Math.round(r.confidence_overall * 100)}%` : '—'}
                            </span>
                          </td>
                          <td>
                            <span className={`badge ${status.cls}`}>{status.label}</span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
            {pg && pg.total_pages > 1 && (
              <div className="card-footer bg-white d-flex justify-content-center gap-2 align-items-center">
                <button className="btn btn-outline-primary btn-sm" disabled={!pg.has_prev} onClick={() => setPage(page - 1)}>
                  ‹
                </button>
                <span className="small text-muted">
                  {pg.page} / {pg.total_pages}
                </span>
                <button className="btn btn-outline-primary btn-sm" disabled={!pg.has_next} onClick={() => setPage(page + 1)}>
                  ›
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Summary */}
        <div className="col-lg-4">
          <div className="card shadow-sm mb-3">
            <div className="card-header bg-white">
              <h6 className="mb-0">{t('summary')}</h6>
            </div>
            <div className="card-body">
              <div className="d-flex justify-content-between py-1">
                <span className="text-muted">{t('ocrTotalRecords')}</span>
                <strong>{total}</strong>
              </div>
              <div className="d-flex justify-content-between py-1">
                <span className="text-muted">{t('reviewed')}</span>
                <strong className="text-success">{reviewed}</strong>
              </div>
              <div className="d-flex justify-content-between py-1">
                <span className="text-muted">{t('ocrPendingReview')}</span>
                <strong className="text-warning">{pending}</strong>
              </div>
            </div>
          </div>
          <Link to="/ocr" className="btn btn-outline-secondary w-100">
            ← {t('ocrBackToList')}
          </Link>
        </div>
      </div>
    </div>
  )
}
