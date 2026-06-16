import { useState } from 'react'
import { Link } from 'react-router-dom'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap, type Paginated } from '../../api/client'
import DeleteAccountDialog, { type DeleteTarget } from '../../components/DeleteAccountDialog'

interface MemberRow {
  id: number
  member_id: string
  full_name: string
  member_type?: string
  form_level?: number
  class_group?: string
  is_active?: boolean
  active_loans?: number
  overdue_loans?: number
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

const GRADUATED = '__graduated__'

/** A clickable, sortable column header. */
function SortTh({
  label,
  field,
  sort,
  order,
  onSort,
  className,
}: {
  label: string
  field: string
  sort: string
  order: 'asc' | 'desc'
  onSort: (field: string) => void
  className?: string
}) {
  const active = sort === field
  return (
    <th className={className} style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => onSort(field)}>
      {label}{' '}
      {active ? (
        <i className={`bi bi-caret-${order === 'asc' ? 'up' : 'down'}-fill small`} />
      ) : (
        <i className="bi bi-arrow-down-up small text-muted opacity-50" />
      )}
    </th>
  )
}

export default function UsersPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<'members' | 'admin'>('members')
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [sort, setSort] = useState('created_at')
  const [order, setOrder] = useState<'asc' | 'desc'>('desc')
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [del, setDel] = useState<DeleteTarget | null>(null)
  const [msg, setMsg] = useState<{ kind: 'success' | 'danger'; text: string } | null>(null)

  const graduated = typeFilter === GRADUATED

  function onSort(field: string) {
    if (sort === field) setOrder(order === 'asc' ? 'desc' : 'asc')
    else {
      setSort(field)
      setOrder('asc')
    }
    setPage(1)
  }

  const { data: members, isLoading: loadingMembers } = useQuery({
    queryKey: ['members', page, search, typeFilter, sort, order],
    queryFn: () =>
      unwrap<Paginated<MemberRow>>(
        api.get('/api/users/members', {
          params: {
            page,
            per_page: 20,
            search,
            sort,
            order,
            ...(graduated ? { graduated: true } : typeFilter ? { type: typeFilter } : {}),
          },
        }),
      ),
    placeholderData: keepPreviousData,
    enabled: tab === 'members',
  })

  const { data: staff, isLoading: loadingStaff } = useQuery({
    queryKey: ['staff', page, search, roleFilter, sort, order],
    queryFn: () =>
      unwrap<Paginated<StaffRow>>(
        api.get('/api/users/staff', {
          params: { page, per_page: 20, search, sort, order, ...(roleFilter && { role: roleFilter }) },
        }),
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

  function switchTab(next: 'members' | 'admin') {
    setTab(next)
    setPage(1)
    setSort('created_at')
    setOrder('desc')
    setSelected(new Set())
  }

  function toggleSelect(id: number) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function toggleSelectAll() {
    const ids = members?.items.map((m) => m.id) || []
    setSelected((prev) => (ids.every((id) => prev.has(id)) ? new Set() : new Set(ids)))
  }

  function onDeleted(message: string) {
    setMsg({ kind: 'success', text: message })
    setDel(null)
    setSelected(new Set())
    queryClient.invalidateQueries({ queryKey: ['members'] })
    queryClient.invalidateQueries({ queryKey: ['staff'] })
  }

  const pg = tab === 'members' ? members?.pagination : staff?.pagination
  const isLoading = tab === 'members' ? loadingMembers : loadingStaff
  const allChecked = !!members?.items.length && members.items.every((m) => selected.has(m.id))

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
                style={{ width: 190 }}
                value={typeFilter}
                onChange={(e) => {
                  setTypeFilter(e.target.value)
                  setPage(1)
                  setSelected(new Set())
                }}
              >
                <option value="">{t('allTypes')}</option>
                <option value="Student">{t('students')}</option>
                <option value="Staff">{t('staffTeacher')}</option>
                <option value="External">{t('external')}</option>
                <option value={GRADUATED}>🎓 {t('graduatedFilter')}</option>
              </select>
              <Link to="/users/members/add" className="btn btn-success text-nowrap">
                <i className="bi bi-person-plus me-1" />
                {t('addMember')}
              </Link>
              <Link
                to="/users/members/import"
                className="btn btn-outline-secondary text-nowrap"
                title="Import students from an Excel file"
              >
                <i className="bi bi-file-earmark-excel me-1" />
                {t('import')}
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
                <option value="">{t('allRoles')}</option>
                <option value="Administrator">{t('administrators')}</option>
                <option value="Librarian">{t('librarians')}</option>
                <option value="Library Prefect">{t('libraryPrefects')}</option>
              </select>
              <Link to="/users/staff/add" className="btn btn-success text-nowrap">
                <i className="bi bi-person-plus me-1" />
                {t('addStaff')}
              </Link>
            </>
          )}
        </div>
      </div>

      {msg && <div className={`alert alert-${msg.kind} py-2`}>{msg.text}</div>}

      <ul className="nav nav-tabs mb-3">
        <li className="nav-item">
          <button className={`nav-link ${tab === 'members' ? 'active' : ''}`} onClick={() => switchTab('members')}>
            <i className="bi bi-people me-1" />
            {t('membersTab')}
          </button>
        </li>
        <li className="nav-item">
          <button className={`nav-link ${tab === 'admin' ? 'active' : ''}`} onClick={() => switchTab('admin')}>
            <i className="bi bi-person-badge me-1" />
            {t('administration')}
          </button>
        </li>
      </ul>

      {graduated && (
        <div className="alert alert-warning d-flex justify-content-between align-items-center py-2">
          <span>
            <i className="bi bi-mortarboard me-1" />
            {t('graduatedHint')}
          </span>
          {selected.size > 0 && (
            <button
              className="btn btn-danger btn-sm"
              onClick={() =>
                setDel({ kind: 'member', ids: [...selected], label: `${selected.size} graduated student(s)` })
              }
            >
              <i className="bi bi-trash me-1" />
              {t('deleteSelected')} ({selected.size})
            </button>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="text-muted py-5 text-center">{t('loading')}</div>
      ) : tab === 'members' ? (
        <div className="card">
          <table className="table table-hover mb-0 align-middle">
            <thead className="table-light">
              <tr>
                {graduated && (
                  <th style={{ width: 36 }}>
                    <input type="checkbox" className="form-check-input" checked={allChecked} onChange={toggleSelectAll} />
                  </th>
                )}
                <SortTh label="ID" field="member_id" sort={sort} order={order} onSort={onSort} />
                <SortTh label={t('name')} field="full_name" sort={sort} order={order} onSort={onSort} />
                <SortTh label={t('type')} field="member_type" sort={sort} order={order} onSort={onSort} />
                <SortTh label={t('formClass')} field="form_level" sort={sort} order={order} onSort={onSort} />
                <th className="text-center">{t('loans')}</th>
                <th className="text-end">{t('actions')}</th>
              </tr>
            </thead>
            <tbody>
              {members?.items.map((m) => {
                const type = m.member_type || 'Student'
                return (
                  <tr key={m.id}>
                    {graduated && (
                      <td>
                        <input
                          type="checkbox"
                          className="form-check-input"
                          checked={selected.has(m.id)}
                          onChange={() => toggleSelect(m.id)}
                        />
                      </td>
                    )}
                    <td>{m.member_id}</td>
                    <td>
                      {m.full_name}
                      {m.is_active === false && <span className="badge bg-secondary ms-2">{t('inactive')}</span>}
                    </td>
                    <td>
                      <span className={`badge ${MEMBER_BADGE[type] || 'bg-secondary'}`}>{type}</span>
                    </td>
                    <td>
                      {m.form_level ? `Form ${m.form_level}` : '—'}
                      {m.class_group ? ` ${m.class_group}` : ''}
                    </td>
                    <td className="text-center">
                      {(m.active_loans ?? 0) > 0 ? (
                        <span className="badge bg-primary">{m.active_loans}</span>
                      ) : (
                        <span className="text-muted">0</span>
                      )}
                      {(m.overdue_loans ?? 0) > 0 && (
                        <span className="badge bg-danger ms-1" title="Overdue">
                          {m.overdue_loans}
                        </span>
                      )}
                    </td>
                    <td>
                      <div className="d-flex gap-1 justify-content-end">
                        <Link
                          to={`/users/members/${m.id}/edit`}
                          className="btn btn-outline-primary btn-sm text-nowrap"
                          style={{ width: 80 }}
                        >
                          {t('edit')}
                        </Link>
                        <div style={{ width: 128 }}>
                          {type === 'Student' && (
                            <button
                              className="btn btn-outline-info btn-sm w-100 text-nowrap"
                              title="Promote to Library Prefect"
                              onClick={() =>
                                act(
                                  () => unwrap(api.post(`/api/users/members/${m.id}/promote`)),
                                  `Promote ${m.full_name} to Library Prefect? They move to Administration.`,
                                )
                              }
                            >
                              <i className="bi bi-arrow-up-circle me-1" />
                              {t('prefect')}
                            </button>
                          )}
                          {type === 'Staff' && (
                            <button
                              className="btn btn-outline-info btn-sm w-100 text-nowrap"
                              title="Promote to Librarian"
                              onClick={() =>
                                act(
                                  () => unwrap(api.post(`/api/users/members/${m.id}/promote`)),
                                  `Promote ${m.full_name} to Librarian? They move to Administration.`,
                                )
                              }
                            >
                              <i className="bi bi-arrow-up-circle me-1" />
                              {t('librarianRole')}
                            </button>
                          )}
                        </div>
                        <button
                          className="btn btn-outline-danger btn-sm"
                          title={t('delete')}
                          onClick={() => setDel({ kind: 'member', ids: [m.id], label: `${m.full_name} (${m.member_id})` })}
                        >
                          <i className="bi bi-trash" />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
              {members?.items.length === 0 && (
                <tr>
                  <td colSpan={graduated ? 7 : 6} className="text-center text-muted py-4">
                    {t('noMembers')}
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
                <SortTh label={t('username').split(' / ')[0]} field="username" sort={sort} order={order} onSort={onSort} />
                <SortTh label={t('name')} field="full_name" sort={sort} order={order} onSort={onSort} />
                <SortTh label={t('email')} field="email" sort={sort} order={order} onSort={onSort} />
                <SortTh label={t('role')} field="role" sort={sort} order={order} onSort={onSort} />
                <th className="text-end">{t('actions')}</th>
              </tr>
            </thead>
            <tbody>
              {staff?.items.map((u) => (
                <tr key={u.id}>
                  <td>{u.username}</td>
                  <td>
                    {u.full_name || '—'}
                    {u.is_active === false && <span className="badge bg-secondary ms-2">{t('inactive')}</span>}
                    {u.promoted_member_type && (
                      <span className="badge bg-light text-muted ms-2" title="Promoted from a library member">
                        {t('promoted')}
                      </span>
                    )}
                  </td>
                  <td>{u.email || '—'}</td>
                  <td>
                    <span className={`badge ${ROLE_BADGE[u.role?.name || ''] || 'bg-secondary'}`}>
                      {u.role?.name || '—'}
                    </span>
                  </td>
                  <td>
                    <div className="d-flex gap-1 justify-content-end">
                      {u.promoted_member_type ? (
                        // Promoted member: edit their info on the member record
                        // (source of truth); manage rank via demote.
                        <>
                          <Link
                            to={`/users/members/${u.linked_member_id}/edit`}
                            className="btn btn-outline-primary btn-sm text-nowrap"
                            style={{ width: 80 }}
                          >
                            {t('edit')}
                          </Link>
                          <button
                            className="btn btn-outline-warning btn-sm text-nowrap"
                            style={{ width: 128 }}
                            title="Demote back to a regular member"
                            onClick={() =>
                              act(
                                () => unwrap(api.post(`/api/users/members/${u.linked_member_id}/demote`)),
                                `Demote ${u.full_name}? They return to the Members list.`,
                              )
                            }
                          >
                            <i className="bi bi-arrow-down-circle me-1" />
                            {t('demote')}
                          </button>
                        </>
                      ) : (
                        <>
                          <Link
                            to={`/users/staff/${u.id}/edit`}
                            className="btn btn-outline-primary btn-sm text-nowrap"
                            style={{ width: 80 }}
                          >
                            {t('edit')}
                          </Link>
                          <button
                            className="btn btn-outline-danger btn-sm text-nowrap"
                            style={{ width: 128 }}
                            title={t('delete')}
                            onClick={() => setDel({ kind: 'staff', ids: [u.id], label: `${u.full_name || u.username} (${u.username})` })}
                          >
                            <i className="bi bi-trash me-1" />
                            {t('delete')}
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {staff?.items.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center text-muted py-4">
                    {t('noAdminAccounts')}
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

      <DeleteAccountDialog target={del} onClose={() => setDel(null)} onDeleted={onDeleted} />
    </div>
  )
}
