import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../api/client'

export default function ChangePasswordPage() {
  const { t } = useTranslation()
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm_password: '' })
  const [msg, setMsg] = useState<{ kind: 'success' | 'danger'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setMsg(null)
    try {
      await unwrap(api.post('/api/auth/change-password', form))
      setMsg({ kind: 'success', text: t('passwordChanged') })
      setForm({ current_password: '', new_password: '', confirm_password: '' })
    } catch (err) {
      setMsg({ kind: 'danger', text: err instanceof Error ? err.message : t('error') })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto" style={{ maxWidth: 480 }}>
      <h4 className="mb-3">{t('changePassword')}</h4>
      {msg && <div className={`alert alert-${msg.kind} py-2`}>{msg.text}</div>}
      <form onSubmit={submit} className="card shadow-sm p-4">
        <div className="mb-3">
          <label className="form-label">{t('currentPassword')}</label>
          <input
            type="password"
            className="form-control"
            value={form.current_password}
            onChange={(e) => setForm({ ...form, current_password: e.target.value })}
            required
          />
        </div>
        <div className="mb-3">
          <label className="form-label">{t('newPassword')}</label>
          <input
            type="password"
            className="form-control"
            value={form.new_password}
            onChange={(e) => setForm({ ...form, new_password: e.target.value })}
            minLength={6}
            required
          />
        </div>
        <div className="mb-4">
          <label className="form-label">{t('confirmNewPassword')}</label>
          <input
            type="password"
            className="form-control"
            value={form.confirm_password}
            onChange={(e) => setForm({ ...form, confirm_password: e.target.value })}
            minLength={6}
            required
          />
        </div>
        <button className="btn btn-primary" disabled={busy}>
          {busy ? t('loading') : t('changePassword')}
        </button>
      </form>
    </div>
  )
}
