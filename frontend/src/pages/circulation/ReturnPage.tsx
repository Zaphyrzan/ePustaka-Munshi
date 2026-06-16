import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../../api/client'

interface CopyLoan {
  id: number
  barcode?: string
  accession_number?: string
  current_loan?: {
    id: number
    member?: { full_name?: string }
    due_date?: string
  }
  book?: { title?: string }
}

/** Scan a returned book's barcode, confirm, mark returned. */
export default function ReturnPage() {
  const { t } = useTranslation()
  const [barcode, setBarcode] = useState('')
  const [found, setFound] = useState<CopyLoan | null>(null)
  const [condition, setCondition] = useState('good')
  const [msg, setMsg] = useState<{ kind: 'success' | 'danger'; text: string } | null>(null)

  async function lookup(e: React.FormEvent) {
    e.preventDefault()
    setMsg(null)
    setFound(null)
    try {
      const res = await api.get(`/circulation/api/copy/${encodeURIComponent(barcode.trim())}/loan`)
      if (!res.data.current_loan) {
        setMsg({ kind: 'danger', text: t('noActiveLoan') })
        return
      }
      setFound(res.data)
    } catch {
      setMsg({ kind: 'danger', text: t('copyNotFound') })
    }
  }

  async function doReturn() {
    if (!found?.current_loan) return
    setMsg(null)
    try {
      await unwrap(api.post('/api/circulation/return', { loan_id: found.current_loan.id, condition }))
      setMsg({ kind: 'success', text: `Returned ${barcode}` })
      setFound(null)
      setBarcode('')
    } catch (err) {
      setMsg({ kind: 'danger', text: err instanceof Error ? err.message : t('error') })
    }
  }

  return (
    <div>
      <h4 className="mb-3">
        <i className="bi bi-box-arrow-in-left me-2" />
        {t('return')}
      </h4>
      <div className="row g-4">
        <div className="col-lg-7">
          {msg && <div className={`alert alert-${msg.kind} py-2`}>{msg.text}</div>}

          <form onSubmit={lookup} className="card shadow-sm p-4 mb-3">
            <label className="form-label fw-bold">{t('bookBarcodeLabel')}</label>
            <div className="d-flex gap-2 align-items-start">
              <div className="input-group flex-grow-1">
                <span className="input-group-text">
                  <i className="bi bi-upc-scan" />
                </span>
                <input
                  className="form-control"
                  value={barcode}
                  onChange={(e) => setBarcode(e.target.value)}
                  placeholder="Scan book barcode"
                  autoFocus
                  required
                />
              </div>
              <button className="btn btn-primary text-nowrap">{t('find')}</button>
            </div>
          </form>

          {found?.current_loan && (
            <div className="card shadow-sm p-4">
              <p className="mb-2">
                <strong>{found.book?.title || found.accession_number}</strong>
                <br />
                <span className="text-muted small">
                  {found.current_loan.member?.full_name || '—'} • {t('dueDate')}{' '}
                  {found.current_loan.due_date?.slice(0, 10) || '—'}
                </span>
              </p>
              <div className="d-flex gap-2 align-items-center">
                <select className="form-select w-auto" value={condition} onChange={(e) => setCondition(e.target.value)}>
                  <option value="good">{t('good')}</option>
                  <option value="damaged">{t('damaged')}</option>
                  <option value="lost">{t('lost')}</option>
                </select>
                <button className="btn btn-success" onClick={doReturn}>
                  <i className="bi bi-check-circle me-1" />
                  {t('confirmReturn')}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Instructions */}
        <div className="col-lg-5">
          <div className="card shadow-sm">
            <div className="card-header bg-white">
              <h6 className="mb-0">
                <i className="bi bi-info-circle me-2" />
                {t('instructions')}
              </h6>
            </div>
            <div className="card-body">
              <ol className="ps-3 mb-3 small">
                <li className="mb-2">{t('reStep1')}</li>
                <li className="mb-2">{t('reStep2')}</li>
                <li className="mb-2">{t('reStep3')}</li>
                <li>{t('reStep4')}</li>
              </ol>
              <div className="alert alert-light border small mb-0">
                <i className="bi bi-lightbulb me-1 text-warning" />
                {t('reNote')}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
