import { useState } from 'react'
import { Link } from 'react-router-dom'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap, type Paginated } from '../../api/client'

interface MemberRow {
  id: number
  member_id: string
  full_name: string
  member_type?: string
  form_level?: number
  class_group?: string
  is_active?: boolean
  active_loans_count?: number
}

interface StaffRow {
  id: number
  username: string
  full_name?: string
  email?: string
  is_active?: boolean
  role?: { name: string }
  promoted_member_type?: string | null
  linked_member_id?: number | null
}

const MEMBER_BADGE: Record<string, string> = {
  Student: 'bg-info text-dark',
  Staff: 'bg-primary',
  External: 'bg-secondary',
}
const ROLE_BADGE: Record<string, string> = {
  Administrator: 'bg-danger',
  Librarian: 'bg-primary',
  'Library Prefect': 'bg-warning text-dark',
}

export default function UsersPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<'members' | 'admin'>('members')
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [msg, setMsg] = useState<{ kind: 'success' | 'danger'; text: string } | null>(null)

  // Detailed delete: confirm with a reason + the admin's password.
  const [del, setDel] = useState<{ kind: 'member' | 'staff'; id: number; name: string } | null>(null)
  const [delReason, setDelReason] = useState('')
  const [delPassword, setDelPassword] = useState('')
  const [delBusy, setDelBusy] = useState(false)
  const [delError, setDelError] = useState('')

  function openDelete(kind: 'member' | 'staff', id: number, name: string) {
    setDel({ kind, id, name })
    setDelReason('')
    setDelPassword('')
    setDelError('')
  }

  async function confirmDelete() {
    if (!del) return
    setDelBusy(true)
    setDelError('')
    const url = del.kind === 'member' ? `/api/users/members/${del.id}` : `/api/users/staff/${del.id}`
    try {
      await unwrap(api.delete(url, { data: { deletion_reason: delReason, current_password: delPassword } }))
      queryClient.invalidateQueries({ queryKey: ['members'] })
      queryClient.invalidateQueries({ queryKey: ['staff'] })
      setMsg({ kind: 'success', text: `${del.name} deleted` })
      setDel(null)
    } catch (err) {
      setDelError(err instanceof Error ? err.message : t('error'))
    } finally {
      setDelBusy(false)
    }
  }

  const { data: members, isLoading: loadingMembers } = useQuery({
    queryKey: ['members', page, search, typeFilter],
    queryFn: () =>
      unwrap<Paginated<MemberRow>>(
        api.get('/api/users/members', {
          params: { page, per_page: 20, search, ...(typeFilter && { type: typeFilter }) },
        }),
      ),
    placeholderData: keepPreviousData,
    enabled: tab === 'members',
  })

  const { data: staff, isLoading: loadingStaff } = useQuery({
    queryKey: ['staff', page, search, roleFilter],
    queryFn: () =>
      unwrap<Paginated<StaffRow>>(
        api.get('/api/users/staff', { params: { page, per_page: 20, search, ...(roleFilter && { role: roleFilter }) } }),
      ),
    placeholderData: keepPreviousData,
    enabled: tab === 'admin',
  })

  function act(fn: () => Promise<unknown>, confirmText?: string) {
    if (confirmText && !confirm(confirmText)) return
    fn()
      .then((res) => {
        const message = (res as { message?: string })?.message
        setMsg({ kind: 'success', text: message || 'Done' })
        queryClient.invalidateQueries({ queryKey: ['members'] })
        queryClient.invalidateQueries({ queryKey: ['staff'] })
      })
      .catch((err) => setMsg({ kind: 'danger', text: err instanceof Error ? err.message : t('error') }))
  }

  const pg = tab === 'members' ? members?.pagination : staff?.pagination
  const isLoading = tab === 'members' ? loadingMembers : loadingStaff

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
        <h4 className="mb-0">{t('users')}</h4>
        <div className="d-flex gap-2 flex-wrap">
          <input
            className="form-control"
            style={{ width: 240 }}
            placeholder={t('search')}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
          />
          {tab === 'members' ? (
            <>
              <select
                className="form-select"
                style={{ width: 170 }}
                value={typeFilter}
                onChange={(e) => {
                  setTypeFilter(e.target.value)
                  setPage(1)
                }}
              >
                <option value="">All types</option>
                <option value="Student">Students</option>
                <option value="Staff">Staff / Teacher</option>
                <option value="External">External</option>
              </select>
              <Link to="/users/members/add" className="btn btn-success text-nowrap">
                <i className="bi bi-person-plus me-1" />
                Add member
              </Link>
              <Link
                to="/users/members/import"
                className="btn btn-outline-secondary text-nowrap"
                title="Import students from an Excel file"
              >
                <i className="bi bi-file-earmark-excel me-1" />
                Import
              </Link>
            </>
          ) : (
            <>
              <select
                className="form-select"
                style={{ width: 180 }}
                value={roleFilter}
                onChange={(e) => {
                  setRoleFilter(e.target.value)
                  setPage(1)
                }}
              >
                <option value="">All roles</option>
                <option value="Administrator">Administrators</option>
                <option value="Librarian">Librarians</option>
                <option value="Library Prefect">Library Prefects</option>
              </select>
              <Link to="/users/staff/add" className="btn btn-success text-nowrap">
                <i className="bi bi-person-plus me-1" />
                Add staff
              </Link>
            </>
          )}
        </div>
      </div>

      {msg && <div className={`alert alert-${msg.kind} py-2`}>{msg.text}</div>}

      <ul className="nav nav-tabs mb-3">
        <li className="nav-item">
          <button
            className={`nav-link ${tab === 'members' ? 'active' : ''}`}
            onClick={() => {
              setTab('members')
              setPage(1)
            }}
          >
            <i className="bi bi-people me-1" />
            Members
          </button>
        </li>
        <li className="nav-item">
          <button
            className={`nav-link ${tab === 'admin' ? 'active' : ''}`}
            onClick={() => {
              setTab('admin')
              setPage(1)
            }}
          >
            <i className="bi bi-person-badge me-1" />
            Administration
          </button>
        </li>
      </ul>

      {isLoading ? (
        <div className="text-muted py-5 text-center">{t('loading')}</div>
      ) : tab === 'members' ? (
        <div className="card">
          <table className="table table-hover mb-0 align-middle">
            <thead className="table-light">
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Type</th>
                <th>Form / Class</th>
                <th className="text-center">Loans</th>
                <th className="text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              {members?.items.map((m) => {
                const type = m.member_type || 'Student'
                return (
                  <tr key={m.id}>
                    <td>{m.member_id}</td>
                    <td>
                      {m.full_name}
                      {m.is_active === false && <span className="badge bg-secondary ms-2">inactive</span>}
                    </td>
                    <td>
                      <span className={`badge ${MEMBER_BADGE[type] || 'bg-secondary'}`}>{type}</span>
                    </td>
                    <td>
                      {m.form_level ? `Form ${m.form_level}` : '—'}
                      {m.class_group ? ` ${m.class_group}` : ''}
                    </td>
                    <td className="text-center">{m.active_loans_count ?? 0}</td>
                    <td className="text-end text-nowrap">
                      <Link to={`/users/members/${m.id}/edit`} className="btn btn-outline-primary btn-sm me-1">
                        Edit
                      </Link>
                      {type === 'Student' && (
                        <button
                          className="btn btn-outline-info btn-sm me-1"
                          title="Promote to Library Prefect"
                          onClick={() =>
                            act(
                              () => unwrap(api.post(`/api/users/members/${m.id}/promote`)),
                              `Promote ${m.full_name} to Library Prefect? They move to Administration.`,
                            )
                          }
                        >
                          <i className="bi bi-arrow-up-circle me-1" />
                          Prefect
                        </button>
                      )}
                      {type === 'Staff' && (
                        <button
                          className="btn btn-outline-info btn-sm me-1"
                          title="Promote to Librarian"
                          onClick={() =>
                            act(
                              () => unwrap(api.post(`/api/users/members/${m.id}/promote`)),
                              `Promote ${m.full_name} to Librarian? They move to Administration.`,
                            )
                          }
                        >
                          <i className="bi bi-arrow-up-circle me-1" />
                          Librarian
                        </button>
                      )}
                      <button
                        className="btn btn-outline-danger btn-sm"
                        title="Delete member"
                        onClick={() => openDelete('member', m.id, `${m.full_name} (${m.member_id})`)}
                      >
                        <i className="bi bi-trash" />
                      </button>
                    </td>
                  </tr>
                )
              })}
              {members?.items.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center text-muted py-4">
                    No members
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="card">
          <table className="table table-hover mb-0 align-middle">
            <thead className="table-light">
              <tr>
                <th>Username</th>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th className="text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              {staff?.items.map((u) => (
                <tr key={u.id}>
                  <td>{u.username}</td>
                  <td>
                    {u.full_name || '—'}
                    {u.is_active === false && <span className="badge bg-secondary ms-2">inactive</span>}
                    {u.promoted_member_type && (
                      <span className="badge bg-light text-muted ms-2" title="Promoted from a library member">
                        promoted
                      </span>
                    )}
                  </td>
                  <td>{u.email || '—'}</td>
                  <td>
                    <span className={`badge ${ROLE_BADGE[u.role?.name || ''] || 'bg-secondary'}`}>
                      {u.role?.name || '—'}
                    </span>
                  </td>
                  <td className="text-end text-nowrap">
                    {u.promoted_member_type ? (
                      // Promoted member: edit their info on the member record
                      // (source of truth); manage rank via demote.
                      <>
                        <Link
                          to={`/users/members/${u.linked_member_id}/edit`}
                          className="btn btn-outline-primary btn-sm me-1"
                        >
                          Edit
                        </Link>
                        <button
                          className="btn btn-outline-warning btn-sm me-1"
                          title="Demote back to a regular member"
                          onClick={() =>
                            act(
                              () => unwrap(api.post(`/api/users/members/${u.linked_member_id}/demote`)),
                              `Demote ${u.full_name}? They return to the Members list.`,
                            )
                          }
                        >
                          <i className="bi bi-arrow-down-circle me-1" />
                          Demote
                        </button>
                      </>
                    ) : (
                      <>
                        <Link to={`/users/staff/${u.id}/edit`} className="btn btn-outline-primary btn-sm me-1">
                          Edit
                        </Link>
                        <button
                          className="btn btn-outline-danger btn-sm"
                          title="Delete account"
                          onClick={() => openDelete('staff', u.id, `${u.full_name || u.username} (${u.username})`)}
                        >
                          <i className="bi bi-trash" />
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
              {staff?.items.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center text-muted py-4">
                    No administration accounts
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {pg && pg.total_pages > 1 && (
        <nav className="d-flex justify-content-center mt-3 gap-2">
          <button className="btn btn-outline-primary btn-sm" disabled={!pg.has_prev} onClick={() => setPage(page - 1)}>
            ‹
          </button>
          <span className="align-self-center small text-muted">
            {pg.page} / {pg.total_pages}
          </span>
          <button className="btn btn-outline-primary btn-sm" disabled={!pg.has_next} onClick={() => setPage(page + 1)}>
            ›
          </button>
        </nav>
      )}

      {del && (
        <>
          <div className="modal-backdrop fade show" />
          <div className="modal fade show d-block" tabIndex={-1} role="dialog">
            <div className="modal-dialog modal-dialog-centered" role="document">
              <div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title text-danger">
                    <i className="bi bi-exclamation-triangle me-2" />
                    Delete account
                  </h5>
                  <button type="button" className="btn-close" onClick={() => setDel(null)} disabled={delBusy} />
                </div>
                <div className="modal-body">
                  <p className="mb-3">
                    You are about to permanently delete <strong>{del.name}</strong>. Historical loan records are kept
                    for audit. This cannot be undone.
                  </p>
                  {delError && <div className="alert alert-danger py-2">{delError}</div>}
                  <div className="mb-3">
                    <label className="form-label">Reason for deletion</label>
                    <textarea
                      className="form-control"
                      rows={2}
                      maxLength={200}
                      placeholder="e.g. Graduated and left the school"
                      value={delReason}
                      onChange={(e) => setDelReason(e.target.value)}
                    />
                  </div>
                  <div className="mb-1">
                    <label className="form-label">Confirm your password</label>
                    <input
                      type="password"
                      autoComplete="current-password"
                      className="form-control"
                      placeholder="Your account password"
                      value={delPassword}
                      onChange={(e) => setDelPassword(e.target.value)}
                    />
                  </div>
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-outline-secondary" onClick={() => setDel(null)} disabled={delBusy}>
                    Cancel
                  </button>
                  <button type="button" className="btn btn-danger" onClick={confirmDelete} disabled={delBusy || !delPassword}>
                    {delBusy ? t('loading') : 'Delete permanently'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
