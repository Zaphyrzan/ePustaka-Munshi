import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../api/client'

export interface DeleteTarget {
  kind: 'member' | 'staff'
  ids: number[]
  label: string // e.g. "Ali (STU0001)" or "12 graduated students"
}

/**
 * Detailed delete confirmation (mirrors the old Flask flow): captures a
 * reason and requires the admin's password. Handles single member, single
 * staff, and bulk member deletes.
 */
export default function DeleteAccountDialog({
  target,
  onClose,
  onDeleted,
}: {
  target: DeleteTarget | null
  onClose: () => void
  onDeleted: (message: string) => void
}) {
  const { t } = useTranslation()
  const [reason, setReason] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setReason('')
    setPassword('')
    setError('')
  }, [target])

  if (!target) return null
  const bulk = target.kind === 'member' && target.ids.length > 1

  async function submit() {
    if (!target) return
    setBusy(true)
    setError('')
    try {
      let message = `${target.label} deleted`
      if (bulk) {
        const res = await unwrap<{ deleted: string[]; skipped: string[] }>(
          api.post('/api/users/members/bulk-delete', {
            ids: target.ids,
            deletion_reason: reason,
            current_password: password,
          }),
        )
        message =
          `${res.deleted.length} member(s) deleted` +
          (res.skipped.length ? ` — ${res.skipped.length} skipped (active loans)` : '')
      } else {
        const id = target.ids[0]
        const url = target.kind === 'member' ? `/api/users/members/${id}` : `/api/users/staff/${id}`
        await unwrap(api.delete(url, { data: { deletion_reason: reason, current_password: password } }))
      }
      onDeleted(message)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('error'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="modal-backdrop fade show" />
      <div className="modal fade show d-block" tabIndex={-1} role="dialog">
        <div className="modal-dialog modal-dialog-centered" role="document">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title text-danger">
                <i className="bi bi-exclamation-triangle me-2" />
                {bulk ? 'Delete selected accounts' : 'Delete account'}
              </h5>
              <button type="button" className="btn-close" onClick={onClose} disabled={busy} />
            </div>
            <div className="modal-body">
              <p className="mb-3">
                You are about to permanently delete <strong>{target.label}</strong>. Historical loan records are kept
                for audit. This cannot be undone.
              </p>
              {error && <div className="alert alert-danger py-2">{error}</div>}
              <div className="mb-3">
                <label className="form-label">Reason for deletion</label>
                <textarea
                  className="form-control"
                  rows={2}
                  maxLength={200}
                  placeholder="e.g. Graduated and left the school"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </div>
              <div className="mb-1">
                <label className="form-label">Confirm your password</label>
                <input
                  type="password"
                  autoComplete="current-password"
                  className="form-control"
                  placeholder="Your account password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-outline-secondary" onClick={onClose} disabled={busy}>
                Cancel
              </button>
              <button type="button" className="btn btn-danger" onClick={submit} disabled={busy || !password}>
                {busy ? t('loading') : 'Delete permanently'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
