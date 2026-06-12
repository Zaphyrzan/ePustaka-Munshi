import { useState } from 'react'
import { Link } from 'react-router-dom'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { API_BASE, api, unwrap, type Paginated } from '../../api/client'

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
}

export default function UsersPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<'members' | 'staff'>('members')
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [msg, setMsg] = useState<{ kind: 'success' | 'danger'; text: string } | null>(null)

  const { data: members, isLoading: loadingMembers } = useQuery({
    queryKey: ['members', page, search],
    queryFn: () =>
      unwrap<Paginated<MemberRow>>(api.get('/api/users/members', { params: { page, per_page: 20, search } })),
    placeholderData: keepPreviousData,
    enabled: tab === 'members',
  })

  const { data: staff, isLoading: loadingStaff } = useQuery({
    queryKey: ['staff', page, search],
    queryFn: () =>
      unwrap<Paginated<StaffRow>>(api.get('/api/users/staff', { params: { page, per_page: 20, search } })),
    placeholderData: keepPreviousData,
    enabled: tab === 'staff',
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
        <div className="d-flex gap-2">
          <input
            className="form-control"
            style={{ width: 260 }}
            placeholder={t('search')}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
          />
          {tab === 'members' ? (
            <>
              <Link to="/users/members/add" className="btn btn-success text-nowrap">
                <i className="bi bi-person-plus me-1" />
                Add member
              </Link>
              <a
                className="btn btn-outline-secondary text-nowrap"
                href={`${API_BASE}/users/students/import`}
                target="_blank"
                rel="noreferrer"
                title="Excel import (opens classic page)"
              >
                <i className="bi bi-file-earmark-excel me-1" />
                Import
              </a>
            </>
          ) : (
            <Link to="/users/staff/add" className="btn btn-success text-nowrap">
              <i className="bi bi-person-plus me-1" />
              Add staff
            </Link>
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
            Library Members
          </button>
        </li>
        <li className="nav-item">
          <button
            className={`nav-link ${tab === 'staff' ? 'active' : ''}`}
            onClick={() => {
              setTab('staff')
              setPage(1)
            }}
          >
            <i className="bi bi-person-badge me-1" />
            Staff Accounts
          </button>
        </li>
      </ul>

      {isLoading ? (
        <div className="text-muted py-5 text-center">{t('loading')}</div>
      ) : tab === 'members' ? (
        <div className="card shadow-sm">
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
              {members?.items.map((m) => (
                <tr key={m.id}>
                  <td>{m.member_id}</td>
                  <td>
                    {m.full_name}
                    {m.is_active === false && <span className="badge bg-secondary ms-2">inactive</span>}
                  </td>
                  <td>
                    <span className={`badge ${m.member_type === 'Student' ? 'bg-info text-dark' : 'bg-primary'}`}>
                      {m.member_type || 'Student'}
                    </span>
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
                    {m.member_type === 'Student' ? (
                      <button
                        className="btn btn-outline-info btn-sm me-1"
                        title="Promote to Student Assistant"
                        onClick={() =>
                          act(
                            () => unwrap(api.post(`/api/users/members/${m.id}/promote`)),
                            `Promote ${m.full_name} to Student Assistant?`,
                          )
                        }
                      >
                        <i className="bi bi-arrow-up-circle" />
                      </button>
                    ) : (
                      m.member_type === 'Student Assistant' && (
                        <button
                          className="btn btn-outline-warning btn-sm me-1"
                          title="Demote to Student"
                          onClick={() =>
                            act(() => unwrap(api.post(`/api/users/members/${m.id}/demote`)), `Demote ${m.full_name}?`)
                          }
                        >
                          <i className="bi bi-arrow-down-circle" />
                        </button>
                      )
                    )}
                    <button
                      className="btn btn-outline-danger btn-sm"
                      onClick={() =>
                        act(
                          () => unwrap(api.delete(`/api/users/members/${m.id}`)),
                          `Delete member ${m.full_name}? This cannot be undone.`,
                        )
                      }
                    >
                      <i className="bi bi-trash" />
                    </button>
                  </td>
                </tr>
              ))}
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
        <div className="card shadow-sm">
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
                  </td>
                  <td>{u.email || '—'}</td>
                  <td>
                    <span className="badge bg-primary">{u.role?.name || '—'}</span>
                  </td>
                  <td className="text-end text-nowrap">
                    <Link to={`/users/staff/${u.id}/edit`} className="btn btn-outline-primary btn-sm me-1">
                      Edit
                    </Link>
                    <button
                      className="btn btn-outline-danger btn-sm"
                      onClick={() =>
                        act(
                          () => unwrap(api.delete(`/api/users/staff/${u.id}`)),
                          `Delete staff account ${u.username}?`,
                        )
                      }
                    >
                      <i className="bi bi-trash" />
                    </button>
                  </td>
                </tr>
              ))}
              {staff?.items.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center text-muted py-4">
                    No staff
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
    </div>
  )
}
