import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../../api/client'

interface MemberInfo {
  id: number
  member_id: string
  full_name: string
  member_type?: string
  active_loans_count?: number
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
      setMsg({ kind: 'danger', text: 'Member not found' })
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
    <div className="mx-auto" style={{ maxWidth: 640 }}>
      <h4 className="mb-3">
        <i className="bi bi-box-arrow-right me-2" />
        {t('checkout')}
      </h4>
      {msg && <div className={`alert alert-${msg.kind} py-2`}>{msg.text}</div>}

      <form onSubmit={lookupMember} className="card shadow-sm p-4 mb-3">
        <label className="form-label fw-bold">1. Member ID (scan card or type)</label>
        <div className="d-flex gap-2">
          <input
            className="form-control"
            value={memberCode}
            onChange={(e) => setMemberCode(e.target.value)}
            placeholder="STU0001"
            autoFocus
            required
          />
          <button className="btn btn-primary">Find</button>
        </div>
        {member && (
          <div className="alert alert-info mt-3 mb-0 py-2">
            <strong>{member.full_name}</strong> ({member.member_id})
            {member.member_type && <span className="badge bg-secondary ms-2">{member.member_type}</span>}
          </div>
        )}
      </form>

      <form onSubmit={doCheckout} className="card shadow-sm p-4">
        <label className="form-label fw-bold">2. Book barcode (scan)</label>
        <div className="d-flex gap-2">
          <input
            ref={barcodeRef}
            className="form-control"
            value={barcode}
            onChange={(e) => setBarcode(e.target.value)}
            placeholder="Scan book barcode"
            disabled={!member}
            required
          />
          <button className="btn btn-success" disabled={!member}>
            {t('checkout')}
          </button>
        </div>
      </form>
    </div>
  )
}
