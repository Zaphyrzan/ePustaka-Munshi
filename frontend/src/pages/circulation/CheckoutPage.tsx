import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../../api/client'

interface MemberInfo {
  id: number
  member_id: string
  full_name: string
  member_type?: string
  form_name?: string
  class_group?: string
  active_loans?: number
  overdue_loans?: number
  can_borrow?: boolean
  is_active?: boolean
}

/** Scanner-first checkout: scan member card, then book barcode. */
export default function CheckoutPage() {
  const { t } = useTranslation()
  const [memberCode, setMemberCode] = useState('')
  const [member, setMember] = useState<MemberInfo | null>(null)
  const [barcode, setBarcode] = useState('')
  const [msg, setMsg] = useState<{ kind: 'success' | 'danger'; text: string } | null>(null)
  const barcodeRef = useRef<HTMLInputElement>(null)

  async function lookupMember(e: React.FormEvent) {
    e.preventDefault()
    setMsg(null)
    try {
      // Web JSON helper route (plain payload, no envelope)
      const res = await api.get(`/circulation/api/member/${encodeURIComponent(memberCode.trim())}`)
      setMember(res.data)
      setTimeout(() => barcodeRef.current?.focus(), 50)
    } catch {
      setMember(null)
      setMsg({ kind: 'danger', text: t('memberNotFound') })
    }
  }

  async function doCheckout(e: React.FormEvent) {
    e.preventDefault()
    if (!member) return
    setMsg(null)
    try {
      await unwrap(api.post('/api/circulation/checkout', { barcode: barcode.trim(), member_id: member.id }))
      setMsg({ kind: 'success', text: `Checked out ${barcode} to ${member.full_name}` })
      setBarcode('')
      barcodeRef.current?.focus()
    } catch (err) {
      setMsg({ kind: 'danger', text: err instanceof Error ? err.message : t('error') })
    }
  }

  return (
    <div>
      <h4 className="mb-3">
        <i className="bi bi-box-arrow-right me-2" />
        {t('checkout')}
      </h4>
      <div className="row g-4">
        <div className="col-lg-7">
      {msg && <div className={`alert alert-${msg.kind} py-2`}>{msg.text}</div>}

      <form onSubmit={lookupMember} className="card shadow-sm p-4 mb-3">
        <label className="form-label fw-bold">1. {t('memberIdLabel')}</label>
        <div className="d-flex gap-2 align-items-start">
          <div className="input-group flex-grow-1">
            <span className="input-group-text">
              <i className="bi bi-person-vcard" />
            </span>
            <input
              className="form-control"
              value={memberCode}
              onChange={(e) => setMemberCode(e.target.value)}
              placeholder="STU0001"
              autoFocus
              required
            />
          </div>
          <button className="btn btn-primary text-nowrap">{t('find')}</button>
        </div>
        {member && (
          <div className={`card mt-3 mb-0 border ${member.can_borrow ? 'border-success' : 'border-danger'}`}>
            <div className="card-body py-3">
              <div className="d-flex justify-content-between align-items-start">
                <div>
                  <h6 className="mb-1">
                    {member.full_name}{' '}
                    <span className="text-muted small fw-normal">({member.member_id})</span>
                  </h6>
                  <div className="small text-muted">
                    {member.member_type === 'Library Prefect' ? 'Library Prefect' : member.member_type || 'Student'}
                    {member.form_name ? ` • ${member.form_name}` : ''}
                    {member.class_group ? ` ${member.class_group}` : ''}
                  </div>
                </div>
                {member.can_borrow ? (
                  <span className="badge bg-success fs-6">✓ {t('canBorrow')}</span>
                ) : (
                  <span className="badge bg-danger fs-6">✗ {t('cannotBorrow')}</span>
                )}
              </div>
              <div className="d-flex gap-4 mt-2 small">
                <span>
                  <i className="bi bi-journal-bookmark me-1" />
                  Active loans: <strong>{member.active_loans ?? 0}</strong>
                </span>
                {(member.overdue_loans ?? 0) > 0 && (
                  <span className="text-danger">
                    <i className="bi bi-exclamation-triangle me-1" />
                    Overdue: <strong>{member.overdue_loans}</strong>
                  </span>
                )}
                {member.is_active === false && <span className="text-danger">Account inactive</span>}
              </div>
              {!member.can_borrow && (
                <div className="alert alert-danger py-2 mt-2 mb-0 small">
                  {(member.overdue_loans ?? 0) > 0
                    ? 'This member has overdue books and cannot borrow until they are returned.'
                    : member.is_active === false
                      ? 'This member account is inactive.'
                      : 'This member has reached the maximum number of loans.'}
                </div>
              )}
            </div>
          </div>
        )}
      </form>

      <form onSubmit={doCheckout} className="card shadow-sm p-4">
        <label className="form-label fw-bold">2. {t('bookBarcodeLabel')}</label>
        <div className="d-flex gap-2 align-items-start">
          <div className="input-group flex-grow-1">
            <span className="input-group-text">
              <i className="bi bi-upc-scan" />
            </span>
            <input
              ref={barcodeRef}
              className="form-control"
              value={barcode}
              onChange={(e) => setBarcode(e.target.value)}
              placeholder="Scan book barcode"
              disabled={!member || !member.can_borrow}
              required
            />
          </div>
          <button className="btn btn-success text-nowrap" disabled={!member || !member.can_borrow}>
            <i className="bi bi-check-circle me-1" />
            {t('processCheckout')}
          </button>
        </div>
        {member && !member.can_borrow && (
          <div className="small text-danger mt-2">{t('cannotBorrow')}</div>
        )}
      </form>
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
                <li className="mb-2">{t('coStep1')}</li>
                <li className="mb-2">{t('coStep2')}</li>
                <li className="mb-2">{t('coStep3')}</li>
                <li className="mb-2">{t('coStep4')}</li>
                <li>{t('coStep5')}</li>
              </ol>
              <div className="alert alert-light border small mb-0">
                <i className="bi bi-lightbulb me-1 text-warning" />
                {t('coNote')}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
