import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../../api/client'

interface CurrentLoan {
  id: number
  member_name?: string
  member_card?: string
  book_title?: string
  accession_number?: string
  checkout_date?: string
  due_date?: string
  status?: string
  is_overdue?: boolean
  days_overdue?: number
}

interface CopyLoan {
  id: number
  barcode?: string
  accession_number?: string
  current_loan?: CurrentLoan
  book?: { title?: string }
}

function fmtDate(iso?: string) {
  if (!iso) return '—'
  const [y, m, d] = iso.slice(0, 10).split('-')
  return `${d}/${m}/${y}`
}

/** Scan a returned book's barcode, confirm the borrower and loan, mark returned. */
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
    const cl = found?.current_loan
    if (!cl) return
    setMsg(null)
    const title = cl.book_title || found?.book?.title || cl.accession_number || barcode
    const who = cl.member_name
    try {
      await unwrap(api.post('/api/circulation/return', { loan_id: cl.id, condition }))
      setMsg({ kind: 'success', text: `${t('returned')}: ${title}${who ? ` — ${who}` : ''}` })
      setFound(null)
      setBarcode('')
    } catch (err) {
      setMsg({ kind: 'danger', text: err instanceof Error ? err.message : t('error') })
    }
  }

  const cl = found?.current_loan
  const overdue = !!cl?.is_overdue

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

          {cl && (
            <div className="card shadow-sm">
              <div className="card-header bg-white d-flex justify-content-between align-items-center">
                <h6 className="mb-0">
                  <i className="bi bi-journal-arrow-down me-2" />
                  {t('confirmReturn')}
                </h6>
                {overdue ? (
                  <span className="badge bg-danger">
                    {cl.days_overdue ? t('loanOverdueDays', { count: cl.days_overdue }) : t('overdue')}
                  </span>
                ) : (
                  <span className="badge bg-success">{t('onLoan')}</span>
                )}
              </div>
              <div className="card-body">
                {/* What is being returned */}
                <div className="mb-3">
                  <div className="fw-bold fs-5">{cl.book_title || found?.book?.title || cl.accession_number}</div>
                  <div className="text-muted small">
                    {t('accessionNo')}: {cl.accession_number || '—'}
                    {found?.barcode ? ` · ${t('barcode')}: ${found.barcode}` : ''}
                  </div>
                </div>

                {/* Who borrowed it + the loan dates */}
                <dl className="row small mb-3">
                  <dt className="col-5 col-sm-4 text-muted fw-normal">
                    <i className="bi bi-person me-1" />
                    {t('borrower')}
                  </dt>
                  <dd className="col-7 col-sm-8 fw-semibold mb-2">
                    {cl.member_name || '—'}
                    {cl.member_card ? <span className="text-muted fw-normal"> ({cl.member_card})</span> : null}
                  </dd>

                  <dt className="col-5 col-sm-4 text-muted fw-normal">{t('loanDate')}</dt>
                  <dd className="col-7 col-sm-8 mb-2">{fmtDate(cl.checkout_date)}</dd>

                  <dt className="col-5 col-sm-4 text-muted fw-normal">{t('dueDate')}</dt>
                  <dd className={`col-7 col-sm-8 mb-0 ${overdue ? 'text-danger fw-semibold' : ''}`}>
                    {fmtDate(cl.due_date)}
                    {overdue && cl.days_overdue ? ` · ${t('loanOverdueDays', { count: cl.days_overdue })}` : ''}
                  </dd>
                </dl>

                {/* Condition assessment + confirm */}
                <div className="d-flex gap-2 align-items-center flex-wrap">
                  <label className="small text-muted mb-0">{t('condition')}</label>
                  <select
                    className="form-select w-auto"
                    value={condition}
                    onChange={(e) => setCondition(e.target.value)}
                  >
                    <option value="good">{t('good')}</option>
                    <option value="damaged">{t('damaged')}</option>
                    <option value="lost">{t('lost')}</option>
                  </select>
                  <button className="btn btn-success ms-auto" onClick={doReturn}>
                    <i className="bi bi-check-circle me-1" />
                    {t('confirmReturn')}
                  </button>
                </div>
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
