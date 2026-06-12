import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../../api/client'

const ROLES = ['Administrator', 'Librarian', 'Student Assistant']

const EMPTY = { username: '', full_name: '', email: '', role: 'Librarian', password: '', is_active: true }

export default function StaffFormPage() {
  const { userId } = useParams()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!userId) return
    unwrap<{ username: string; full_name?: string; email?: string; role?: { name: string }; is_active?: boolean }>(
      api.get(`/api/users/staff/${userId}`),
    ).then((u) =>
      setForm({
        username: u.username || '',
        full_name: u.full_name || '',
        email: u.email || '',
        role: u.role?.name || 'Librarian',
        password: '',
        is_active: u.is_active !== false,
      }),
    )
  }, [userId])

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    const payload: Record<string, unknown> = { ...form }
    if (!form.password) delete payload.password
    try {
      if (userId) await unwrap(api.put(`/api/users/staff/${userId}`, payload))
      else await unwrap(api.post('/api/users/staff', payload))
      queryClient.invalidateQueries({ queryKey: ['staff'] })
      navigate('/users')
    } catch (err) {
      setError(err instanceof Error ? err.message : t('error'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto" style={{ maxWidth: 560 }}>
      <h4 className="mb-3">{userId ? 'Edit Staff Account' : 'Add Staff Account'}</h4>
      {error && <div className="alert alert-danger py-2">{error}</div>}
      <form onSubmit={submit} className="card shadow-sm p-4">
        <div className="mb-3">
          <label className="form-label">Username</label>
          <input
            className="form-control"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            required
            disabled={!!userId}
          />
        </div>
        <div className="mb-3">
          <label className="form-label">Full name</label>
          <input
            className="form-control"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          />
        </div>
        <div className="mb-3">
          <label className="form-label">Email</label>
          <input
            type="email"
            className="form-control"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
          />
        </div>
        <div className="mb-3">
          <label className="form-label">Role</label>
          <select
            className="form-select"
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
          >
            {ROLES.map((r) => (
              <option key={r}>{r}</option>
            ))}
          </select>
        </div>
        <div className="mb-3">
          <label className="form-label">{userId ? 'New password (leave blank to keep)' : 'Password'}</label>
          <input
            type="password"
            className="form-control"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required={!userId}
            minLength={6}
          />
        </div>
        <div className="form-check mb-4">
          <input
            id="active"
            type="checkbox"
            className="form-check-input"
            checked={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
          />
          <label htmlFor="active" className="form-check-label">
            Active
          </label>
        </div>
        <div className="d-flex gap-2">
          <button className="btn btn-primary" disabled={busy}>
            {busy ? t('loading') : userId ? 'Save changes' : 'Add staff'}
          </button>
          <button type="button" className="btn btn-outline-secondary" onClick={() => navigate('/users')}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
