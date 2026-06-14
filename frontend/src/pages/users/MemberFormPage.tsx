import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../../api/client'

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
}

export default function MemberFormPage() {
  const { memberId } = useParams()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const { data: classGroups } = useQuery({
    queryKey: ['class-groups'],
    queryFn: () => unwrap<string[]>(api.get('/api/users/class-groups')),
  })

  function onClassChange(value: string) {
    if (value === ADD_NEW_CLASS) {
      const name = window.prompt('New class name (e.g. Bestari):')?.trim()
      if (!name) return
      api.post('/api/users/class-groups', { name }).catch(() => {})
      queryClient.invalidateQueries({ queryKey: ['class-groups'] })
      setForm((f) => ({ ...f, class_group: name }))
    } else {
      setForm((f) => ({ ...f, class_group: value }))
    }
  }

  useEffect(() => {
    if (!memberId) return
    unwrap<typeof EMPTY & { form_level?: number }>(api.get(`/api/users/members/${memberId}`)).then((m) =>
      setForm({
        member_id: m.member_id || '',
        full_name: m.full_name || '',
        email: m.email || '',
        phone: m.phone || '',
        member_type: m.member_type || 'Student',
        form_level: m.form_level ? String(m.form_level) : '1',
        class_group: m.class_group || '',
        password: '',
      }),
    )
  }, [memberId])

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    const payload: Record<string, unknown> = {
      ...form,
      form_level: form.member_type === 'Student' ? Number(form.form_level) : null,
    }
    if (!form.password) delete payload.password
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
              onChange={(e) => setForm({ ...form, member_id: e.target.value })}
              placeholder="STU0001"
              required
              disabled={!!memberId}
            />
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
              <option>Student</option>
              <option>Staff</option>
              <option>External</option>
            </select>
          </div>
          {form.member_type === 'Student' && (
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
              </div>
            </>
          )}
          <div className="col-md-6 mb-3">
            <label className="form-label">{memberId ? 'New password (leave blank to keep)' : 'Password (optional)'}</label>
            <input
              type="password"
              className="form-control"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </div>
        </div>
        <div className="d-flex gap-2">
          <button className="btn btn-primary" disabled={busy}>
            {busy ? t('loading') : memberId ? 'Save changes' : 'Add member'}
          </button>
          <button type="button" className="btn btn-outline-secondary" onClick={() => navigate('/users')}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
