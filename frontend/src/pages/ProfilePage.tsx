import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../api/client'

interface MeUser {
  id: number
  username?: string
  member_id?: string
  full_name?: string
  email?: string
  phone?: string
  member_type?: string
  class_group?: string
  form_name?: string
  is_active?: boolean
  last_login?: string
  role?: { name?: string }
}
interface Me {
  user: MeUser
  role: string
  user_type: 'staff' | 'student'
}

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="col-md-6 mb-3">
      <label className="text-muted small">{label}</label>
      <p className="mb-0 fw-bold">{value || '—'}</p>
    </div>
  )
}

export default function ProfilePage() {
  const { t } = useTranslation()
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['me-profile'],
    queryFn: () => unwrap<Me>(api.get('/api/auth/me')),
  })

  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ email: '', phone: '' })
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ kind: 'success' | 'danger'; text: string } | null>(null)

  useEffect(() => {
    if (data) setForm({ email: data.user.email || '', phone: data.user.phone || '' })
  }, [data])

  if (isLoading || !data) return <div className="text-muted py-5 text-center">{t('loading')}</div>

  const u = data.user
  const isMember = data.user_type === 'student'

  async function saveContact() {
    setBusy(true)
    setMsg(null)
    try {
      const payload: Record<string, string> = { email: form.email }
      if (isMember) payload.phone = form.phone
      await unwrap(api.put('/api/auth/me', payload))
      await refetch()
      setEditing(false)
      setMsg({ kind: 'success', text: 'Profile updated' })
    } catch (err) {
      setMsg({ kind: 'danger', text: err instanceof Error ? err.message : t('error') })
    } finally {
      setBusy(false)
    }
  }
  const loginId = u.username || u.member_id || '—'
  const lastLogin = u.last_login ? new Date(u.last_login).toLocaleString('en-GB') : 'Never'

  return (
    <div className="mx-auto" style={{ maxWidth: 820 }}>
      <h3 className="mb-3">{t('profile')}</h3>
      {msg && <div className={`alert alert-${msg.kind} py-2`}>{msg.text}</div>}

      {/* Header card */}
      <div className="card mb-4">
        <div className="card-body d-flex align-items-center gap-3">
          <i className="bi bi-person-circle text-primary" style={{ fontSize: '3.5rem' }} />
          <div className="flex-grow-1">
            <h4 className="mb-1">{u.full_name || loginId}</h4>
            <div className="text-muted">
              <span className="badge bg-primary me-2">{data.role}</span>
              {u.email || 'No email set'}
            </div>
          </div>
          <Link to="/change-password" className="btn btn-outline-secondary">
            <i className="bi bi-key me-1" />
            {t('changePassword') || 'Change Password'}
          </Link>
        </div>
      </div>

      {/* Account details */}
      <div className="card mb-4">
        <div className="card-header bg-white d-flex justify-content-between align-items-center">
          <h5 className="mb-0">
            <i className="bi bi-info-circle me-2" />
            Account Details
          </h5>
          {!editing ? (
            <button className="btn btn-outline-primary btn-sm" onClick={() => setEditing(true)}>
              <i className="bi bi-pencil me-1" />
              Edit contact
            </button>
          ) : (
            <div className="d-flex gap-2">
              <button className="btn btn-primary btn-sm" onClick={saveContact} disabled={busy}>
                {busy ? t('loading') : 'Save'}
              </button>
              <button
                className="btn btn-outline-secondary btn-sm"
                onClick={() => {
                  setEditing(false)
                  setForm({ email: u.email || '', phone: u.phone || '' })
                }}
              >
                Cancel
              </button>
            </div>
          )}
        </div>
        <div className="card-body">
          <div className="row">
            <Field label="Login ID" value={loginId} />
            <Field label="Full Name" value={u.full_name} />
            {editing ? (
              <div className="col-md-6 mb-3">
                <label className="text-muted small">Email</label>
                <input
                  type="email"
                  className="form-control"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                />
              </div>
            ) : (
              <Field label="Email" value={u.email} />
            )}
            {isMember &&
              (editing ? (
                <div className="col-md-6 mb-3">
                  <label className="text-muted small">Phone Number</label>
                  <input
                    className="form-control"
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  />
                </div>
              ) : (
                <Field label="Phone Number" value={u.phone} />
              ))}
            {isMember && <Field label="Class" value={u.class_group || u.form_name} />}
            {isMember && (
              <Field label="Member Type" value={u.member_type === 'Library Prefect' ? 'Library Prefect' : u.member_type} />
            )}
            <Field label="Role" value={data.role} />
            <div className="col-md-6 mb-3">
              <label className="text-muted small">Account Status</label>
              <p className="mb-0">
                <span className={`badge ${u.is_active === false ? 'bg-danger' : 'bg-success'}`}>
                  {u.is_active === false ? 'Inactive' : 'Active'}
                </span>
              </p>
            </div>
            {!isMember && <Field label="Last Login" value={lastLogin} />}
          </div>
        </div>
      </div>

      {/* Security */}
      <div className="card">
        <div className="card-header bg-white">
          <h5 className="mb-0">
            <i className="bi bi-shield-lock me-2" />
            Security
          </h5>
        </div>
        <div className="card-body d-flex justify-content-between align-items-center">
          <div>
            <h6 className="mb-1">Password</h6>
            <span className="text-muted small">Keep your account secure with a strong password.</span>
          </div>
          <Link to="/change-password" className="btn btn-outline-secondary">
            Change Password
          </Link>
        </div>
      </div>
    </div>
  )
}
