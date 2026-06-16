import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap, type Paginated } from '../../api/client'
import SortHeader from '../../components/SortHeader'

export interface OcrJob {
  id: number
  job_name: string
  status: string
  page_count?: number
  created_at?: string
  result_count: number
  reviewed_count: number
  committed_count: number
  ready_to_commit: number
  error_message?: string
}

const STATUS_BADGE: Record<string, string> = {
  pending: 'bg-secondary',
  processing: 'bg-primary',
  completed: 'bg-success',
  reviewed: 'bg-info text-dark',
  committed: 'bg-dark',
  failed: 'bg-danger',
}

export default function OcrJobsPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState('created_at')
  const [order, setOrder] = useState<'asc' | 'desc'>('desc')
  const [msg, setMsg] = useState<{ kind: 'success' | 'danger'; text: string } | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const nameRef = useRef<HTMLInputElement>(null)

  function onSort(field: string) {
    if (sort === field) setOrder(order === 'asc' ? 'desc' : 'asc')
    else {
      setSort(field)
      setOrder('asc')
    }
    setPage(1)
  }

  const { data, isLoading } = useQuery({
    queryKey: ['ocr-jobs', page, sort, order],
    queryFn: () =>
      unwrap<Paginated<OcrJob>>(api.get('/api/ocr/jobs', { params: { page, per_page: 20, sort, order } })),
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  })

  const upload = useMutation({
    mutationFn: async () => {
      const file = fileRef.current?.files?.[0]
      if (!file) throw new Error('Choose a file first')
      const fd = new FormData()
      fd.append('file', file)
      if (nameRef.current?.value) fd.append('job_name', nameRef.current.value)
      return unwrap<OcrJob>(api.post('/api/ocr/jobs', fd, { headers: { 'Content-Type': 'multipart/form-data' } }))
    },
    onSuccess: (job) => {
      setMsg({ kind: 'success', text: `Uploaded as job #${job.id} — click Process to extract` })
      if (fileRef.current) fileRef.current.value = ''
      queryClient.invalidateQueries({ queryKey: ['ocr-jobs'] })
    },
    onError: (err) => setMsg({ kind: 'danger', text: err instanceof Error ? err.message : t('error') }),
  })

  const process = useMutation({
    mutationFn: (jobId: number) => unwrap(api.post(`/api/ocr/jobs/${jobId}/process`, {}, { timeout: 600_000 })),
    onSuccess: () => {
      setMsg({ kind: 'success', text: 'Processing complete — review the extracted rows' })
      queryClient.invalidateQueries({ queryKey: ['ocr-jobs'] })
    },
    onError: (err) => setMsg({ kind: 'danger', text: err instanceof Error ? err.message : t('error') }),
  })

  const deleteJob = useMutation({
    mutationFn: (jobId: number) => unwrap(api.delete(`/api/ocr/jobs/${jobId}`)),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ocr-jobs'] }),
  })

  const pg = data?.pagination

  return (
    <div>
      <h4 className="mb-3">
        <i className="bi bi-file-earmark-text me-2" />
        {t('ocr')}
      </h4>
      {msg && <div className={`alert alert-${msg.kind} py-2`}>{msg.text}</div>}

      <div className="card shadow-sm p-3 mb-4">
        <div className="d-flex gap-2 align-items-end flex-wrap">
          <div>
            <label className="form-label small mb-1">Scanned ledger (PDF/image, ≤10 pages)</label>
            <input ref={fileRef} type="file" className="form-control" accept=".pdf,.png,.jpg,.jpeg,.tiff" />
          </div>
          <div>
            <label className="form-label small mb-1">Job name (optional)</label>
            <input ref={nameRef} className="form-control" placeholder="e.g. Ledger page 4" />
          </div>
          <button className="btn btn-primary" onClick={() => upload.mutate()} disabled={upload.isPending}>
            <i className="bi bi-cloud-arrow-up me-1" />
            {upload.isPending ? t('loading') : 'Upload'}
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-muted py-5 text-center">{t('loading')}</div>
      ) : (
        <div className="card shadow-sm">
          <table className="table table-hover mb-0 align-middle">
            <thead className="table-light">
              <tr>
                <th>#</th>
                <SortHeader label={t('job')} field="job_name" sort={sort} order={order} onSort={onSort} />
                <SortHeader label={t('status')} field="status" sort={sort} order={order} onSort={onSort} />
                <th className="text-center">{t('rows')}</th>
                <th className="text-center">{t('reviewed')}</th>
                <SortHeader
                  label={t('uploaded')}
                  field="created_at"
                  sort={sort}
                  order={order}
                  onSort={onSort}
                  className="text-center"
                />
                <th className="text-end">{t('actions')}</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((job) => (
                <tr key={job.id}>
                  <td>{job.id}</td>
                  <td>
                    <span className="fw-semibold">{job.job_name}</span>
                    {job.error_message && <div className="small text-danger">{job.error_message.slice(0, 80)}</div>}
                  </td>
                  <td>
                    <span className={`badge ${STATUS_BADGE[job.status] || 'bg-secondary'}`}>{job.status}</span>
                  </td>
                  <td className="text-center">{job.result_count}</td>
                  <td className="text-center">{job.reviewed_count}</td>
                  <td className="text-center">{job.committed_count}</td>
                  <td className="text-end">
                    {(job.status === 'pending' || job.status === 'failed') && (
                      <button
                        className="btn btn-primary btn-sm me-1"
                        onClick={() => process.mutate(job.id)}
                        disabled={process.isPending}
                      >
                        {process.isPending ? 'Processing…' : 'Process'}
                      </button>
                    )}
                    {job.result_count > 0 && (
                      <Link to={`/ocr/${job.id}/review`} className="btn btn-success btn-sm me-1">
                        Review
                      </Link>
                    )}
                    <button
                      className="btn btn-outline-danger btn-sm"
                      onClick={() => {
                        if (confirm(`Delete job "${job.job_name}"?`)) deleteJob.mutate(job.id)
                      }}
                    >
                      <i className="bi bi-trash" />
                    </button>
                  </td>
                </tr>
              ))}
              {data?.items.length === 0 && (
                <tr>
                  <td colSpan={7} className="text-center text-muted py-4">
                    No OCR jobs yet — upload a scanned ledger above
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {pg && pg.total_pages > 1 && (
        <nav className="d-flex justify-content-center mt-3 gap-2">
          <button className="btn btn-outline-primary btn-sm" disabled={!pg.has_prev} onClick={() => setPage(page - 1)}>
            ‹
          </button>
          <span className="align-self-center small text-muted">
            {pg.page} / {pg.total_pages}
          </span>
          <button className="btn btn-outline-primary btn-sm" disabled={!pg.has_next} onClick={() => setPage(page + 1)}>
            ›
          </button>
        </nav>
      )}
    </div>
  )
}
