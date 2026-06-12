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
        setMsg({ kind: 'danger', text: 'This copy has no active loan' })
        return
      }
      setFound(res.data)
    } catch {
      setMsg({ kind: 'danger', text: 'Copy not found' })
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
    <div className="mx-auto" style={{ maxWidth: 640 }}>
      <h4 className="mb-3">
        <i className="bi bi-box-arrow-in-left me-2" />
        {t('return')}
      </h4>
      {msg && <div className={`alert alert-${msg.kind} py-2`}>{msg.text}</div>}

      <form onSubmit={lookup} className="card shadow-sm p-4 mb-3">
        <label className="form-label fw-bold">Book barcode (scan)</label>
        <div className="d-flex gap-2">
          <input
            className="form-control"
            value={barcode}
            onChange={(e) => setBarcode(e.target.value)}
            placeholder="Scan book barcode"
            autoFocus
            required
          />
          <button className="btn btn-primary">Find</button>
        </div>
      </form>

      {found?.current_loan && (
        <div className="card shadow-sm p-4">
          <p className="mb-2">
            <strong>{found.book?.title || found.accession_number}</strong>
            <br />
            <span className="text-muted small">
              Borrowed by {found.current_loan.member?.full_name || 'unknown'} • due{' '}
              {found.current_loan.due_date?.slice(0, 10) || '—'}
            </span>
          </p>
          <div className="d-flex gap-2 align-items-center">
            <select className="form-select w-auto" value={condition} onChange={(e) => setCondition(e.target.value)}>
              <option value="good">Good</option>
              <option value="damaged">Damaged</option>
              <option value="lost">Lost</option>
            </select>
            <button className="btn btn-success" onClick={doReturn}>
              Confirm return
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
