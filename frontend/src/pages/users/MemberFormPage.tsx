import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import DeleteAccountDialog, { type DeleteTarget } from '../../components/DeleteAccountDialog'

const ADD_NEW_CLASS = '__add_new__'

const EMPTY = {
  member_id: '',
  full_name: '',
  email: '',
  phone: '',
  member_type: 'Student',
  form_level: '1',
  class_group: '',
  password: '',
  is_active: true,
}

export default function MemberFormPage() {
  const { memberId } = useParams()
  const { t } = useTranslation()
  const { session } = useAuth()
  const isAdmin = session?.role === 'Administrator'
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [del, setDel] = useState<DeleteTarget | null>(null)
  // When editing, the record is fetched; show a loading state instead of a
  // blank form (a cold serverless call can take a second or two).
  const [loading, setLoading] = useState(!!memberId)

  const { data: classGroups } = useQuery({
    queryKey: ['class-groups'],
    queryFn: () => unwrap<string[]>(api.get('/api/users/class-groups')),
  })

  function onClassChange(value: string) {
    if (value === ADD_NEW_CLASS) {
      const name = window.prompt('New class name (e.g. Bestari):')?.trim()
      if (!name) return
      api.post('/api/users/class-groups', { name: name.toUpperCase() }).catch(() => {})
      queryClient.invalidateQueries({ queryKey: ['class-groups'] })
      setForm((f) => ({ ...f, class_group: name.toUpperCase() }))
    } else {
      setForm((f) => ({ ...f, class_group: value }))
    }
  }

  async function deleteClass() {
    const name = form.class_group
    if (!name) return
    if (!window.confirm(`Delete class "${name}" from the list?`)) return
    try {
      await unwrap(api.delete(`/api/users/class-groups/${encodeURIComponent(name)}`))
      queryClient.invalidateQueries({ queryKey: ['class-groups'] })
      setForm((f) => ({ ...f, class_group: '' }))
    } catch (err) {
      // e.g. 409 when members are still assigned to the class
      alert(err instanceof Error ? err.message : 'Could not delete class')
    }
  }

  useEffect(() => {
    if (!memberId) return
    setLoading(true)
    unwrap<typeof EMPTY & { form_level?: number; is_active?: boolean }>(
      api.get(`/api/users/members/${memberId}`),
    )
      .then((m) =>
        setForm({
          member_id: m.member_id || '',
          full_name: m.full_name || '',
          email: m.email || '',
          phone: m.phone || '',
          member_type: m.member_type || 'Student',
          form_level: m.form_level ? String(m.form_level) : '1',
          class_group: m.class_group || '',
          password: '',
          is_active: m.is_active !== false,
        }),
      )
      .catch((err) => setError(err instanceof Error ? err.message : t('error')))
      .finally(() => setLoading(false))
  }, [memberId])

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    // Students and Library Prefects keep their form/class (they are still
    // students in a class); other types have no form level.
    const hasClass = form.member_type === 'Student' || form.member_type === 'Library Prefect'
    const payload: Record<string, unknown> = {
      ...form,
      form_level: hasClass ? Number(form.form_level) : null,
      class_group: hasClass ? form.class_group : null,
    }
    if (memberId) {
      if (!form.password) delete payload.password
    } else {
      delete payload.member_id
      delete payload.password
    }
    try {
      if (memberId) await unwrap(api.put(`/api/users/members/${memberId}`, payload))
      else await unwrap(api.post('/api/users/members', payload))
      queryClient.invalidateQueries({ queryKey: ['members'] })
      navigate('/users')
    } catch (err) {
      setError(err instanceof Error ? err.message : t('error'))
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto" style={{ maxWidth: 640 }}>
        <h4 className="mb-3">Edit Member</h4>
        <div className="card shadow-sm p-5 text-center text-muted">
          <div className="spinner-border text-primary mx-auto mb-3" role="status" />
          <div>{t('loading')}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto" style={{ maxWidth: 640 }}>
      <h4 className="mb-3">{memberId ? 'Edit Member' : 'Add Member'}</h4>
      {error && <div className="alert alert-danger py-2">{error}</div>}
      <form onSubmit={submit} className="card shadow-sm p-4">
        <div className="row">
          <div className="col-md-6 mb-3">
            <label className="form-label">Member ID</label>
            <input
              className="form-control"
              value={form.member_id}
              onChange={(e) => memberId && setForm({ ...form, member_id: e.target.value })}
              placeholder={memberId ? '' : 'Auto-generated (STU/TCH/EXT)'}
              required={!!memberId}
              disabled
            />
            {!memberId && (
              <div className="form-text">Leave blank to auto-generate a standardized ID by member type.</div>
            )}
          </div>
          <div className="col-md-6 mb-3">
            <label className="form-label">Full name</label>
            <input
              className="form-control"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              required
            />
          </div>
          <div className="col-md-6 mb-3">
            <label className="form-label">Email</label>
            <input
              type="email"
              className="form-control"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>
          <div className="col-md-6 mb-3">
            <label className="form-label">Phone</label>
            <input
              className="form-control"
              type="tel"
              autoComplete="off"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
          </div>
          <div className="col-md-4 mb-3">
            <label className="form-label">Type</label>
            <select
              className="form-select"
              value={form.member_type}
              onChange={(e) => setForm({ ...form, member_type: e.target.value })}
            >
              <option value="Student">Student</option>
              <option value="Library Prefect">Library Prefect</option>
              <option value="Staff">Staff / Teacher</option>
              <option value="Librarian">Librarian</option>
              <option value="External">External</option>
            </select>
          </div>
          {(form.member_type === 'Student' || form.member_type === 'Library Prefect') && (
            <>
              <div className="col-md-4 mb-3">
                <label className="form-label">Form level</label>
                <select
                  className="form-select"
                  value={form.form_level}
                  onChange={(e) => setForm({ ...form, form_level: e.target.value })}
                >
                  {[1, 2, 3, 4, 5].map((n) => (
                    <option key={n} value={n}>
                      Form {n}
                    </option>
                  ))}
                </select>
              </div>
              <div className="col-md-4 mb-3">
                <label className="form-label">Class group</label>
                <div className="input-group">
                  <select
                    className="form-select"
                    value={form.class_group}
                    onChange={(e) => onClassChange(e.target.value)}
                  >
                    <option value="">— none —</option>
                    {(classGroups || []).map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                    {form.class_group && !(classGroups || []).includes(form.class_group) && (
                      <option value={form.class_group}>{form.class_group}</option>
                    )}
                    <option value={ADD_NEW_CLASS}>+ Add new class…</option>
                  </select>
                  {form.class_group && (
                    <button
                      type="button"
                      className="btn btn-outline-danger"
                      title="Delete this class from the list"
                      onClick={deleteClass}
                    >
                      <i className="bi bi-trash" />
                    </button>
                  )}
                </div>
              </div>
            </>
          )}
          {memberId ? (
            <div className="col-md-6 mb-3">
              <label className="form-label">New password (leave blank to keep)</label>
              <input
                type="password"
                autoComplete="new-password"
                className="form-control"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </div>
          ) : (
            <div className="col-md-6 mb-3">
              <label className="form-label">{t('defaultPassword')}</label>
              <input className="form-control" value="Munshi123" disabled />
              <div className="form-text">{t('memberDefaultPasswordHelp')}</div>
            </div>
          )}
          {memberId && (
            <div className="col-md-6 mb-3 d-flex align-items-end">
              <div className="form-check">
                <input
                  id="member-active"
                  type="checkbox"
                  className="form-check-input"
                  checked={form.is_active}
                  onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                />
                <label htmlFor="member-active" className="form-check-label">
                  Active account
                  <span className="text-muted small d-block">Uncheck to deactivate (blocks login &amp; borrowing)</span>
                </label>
              </div>
            </div>
          )}
        </div>
        <div className="d-flex gap-2">
          <button className="btn btn-primary" disabled={busy}>
            {busy ? t('loading') : memberId ? 'Save changes' : 'Add member'}
          </button>
          <button type="button" className="btn btn-outline-secondary" onClick={() => navigate('/users')}>
            Cancel
          </button>
          {memberId && isAdmin && (
            <button
              type="button"
              className="btn btn-outline-danger ms-auto"
              onClick={() => setDel({ kind: 'member', ids: [Number(memberId)], label: `${form.full_name} (${form.member_id})` })}
            >
              <i className="bi bi-trash me-1" />
              Delete member
            </button>
          )}
        </div>
      </form>

      <DeleteAccountDialog
        target={del}
        onClose={() => setDel(null)}
        onDeleted={() => {
          queryClient.invalidateQueries({ queryKey: ['members'] })
          navigate('/users')
        }}
      />
    </div>
  )
}
