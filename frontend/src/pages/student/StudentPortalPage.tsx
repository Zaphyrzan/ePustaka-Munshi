import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { loanBadge, type Book, type Loan } from '../../types'

// ---- Shapes returned by the student API (see app/api/student_api.py) ----

/** GET /api/student/dashboard - library stats + this member's loans. */
interface DashboardData {
  stats: { total_books: number; available_copies: number; books_read: number }
  member: { active_loans?: number; overdue_loans?: number; class_group?: string } | null
  my_loans: Loan[]
  overdue: Loan[]
}

/** One row in the student ranking. */
interface StudentRank {
  rank?: number
  member_id?: string
  full_name?: string
  form_level?: number
  class_group?: string
  borrow_count?: number
}

/** One row in the per-class ranking. */
interface ClassRank {
  form_level?: number
  class_group?: string
  borrow_count?: number
}

/** GET /api/student/leaderboard - student ranking + class ranking + filters. */
interface LeaderboardData {
  forms: number[]
  selected_form: number | null
  students: StudentRank[]
  top_classes: ClassRank[]
}

/** A small stat tile - mirrors the one used on the staff dashboard. */
function StatCard({ icon, label, value, color }: { icon: string; label: string; value: string | number; color: string }) {
  return (
    <div className="col-6 col-xl-3">
      <div className="card stat-card h-100">
        <div className="card-body d-flex align-items-center">
          <div className={`stat-icon bg-${color} bg-opacity-10 text-${color} me-3`}>
            <i className={`bi ${icon}`} />
          </div>
          <div>
            <div className="text-muted small">{label}</div>
            <div className="fs-4 fw-bold">{value}</div>
          </div>
        </div>
      </div>
    </div>
  )
}

/** Student-facing portal: quick stats, my loans, search, and the NILAM leaderboard. */
export default function StudentPortalPage() {
  const { session } = useAuth()
  const { t } = useTranslation()
  const [tab, setTab] = useState<'loans' | 'search' | 'leaderboard'>('loans')
  const [query, setQuery] = useState('')
  const [submitted, setSubmitted] = useState('')
  const [form, setForm] = useState<number | ''>('') // leaderboard "Form" filter (empty = all)

  // Library + personal stats for the cards at the top. Loaded once on mount
  // (no `enabled` flag) so the numbers are always visible on the home page.
  const { data: dash } = useQuery({
    queryKey: ['student-dashboard'],
    queryFn: () => unwrap<DashboardData>(api.get('/api/student/dashboard')),
  })

  const { data: loans } = useQuery({
    queryKey: ['student-loans'],
    queryFn: () =>
      unwrap<{ active?: { items?: Loan[] }; history?: { items?: Loan[] } }>(api.get('/api/student/loans')),
    enabled: tab === 'loans',
  })

  const { data: results } = useQuery({
    queryKey: ['student-search', submitted],
    queryFn: () => unwrap<{ items?: Book[] } | Book[]>(api.get('/api/student/search', { params: { q: submitted } })),
    enabled: tab === 'search' && !!submitted,
  })

  // Re-fetch when the Form filter changes so the ranking follows the selection.
  const { data: leaderboard } = useQuery({
    queryKey: ['leaderboard', form],
    queryFn: () =>
      unwrap<LeaderboardData>(api.get('/api/student/leaderboard', { params: form ? { form } : {} })),
    enabled: tab === 'leaderboard',
  })

  const loanItems: Loan[] = loans?.active?.items ?? []
  const bookItems: Book[] = Array.isArray(results) ? results : (results?.items ?? [])
  const students: StudentRank[] = leaderboard?.students ?? []
  const topClasses: ClassRank[] = leaderboard?.top_classes ?? []
  const forms: number[] = leaderboard?.forms ?? []

  // Stat values (default to 0 while the dashboard request is in flight).
  const totalBooks = dash?.stats.total_books ?? 0
  const availableBooks = dash?.stats.available_copies ?? 0
  const overdueCount = dash?.member?.overdue_loans ?? 0
  // "Borrowed" = books currently out. An overdue book is still borrowed, so we
  // add active + overdue rather than showing active-only (which could read 0).
  const borrowedCount = (dash?.member?.active_loans ?? 0) + overdueCount

  return (
    <div>
      <h4 className="mb-1">
        {t('welcomeBack')}, {session?.user.full_name}
      </h4>
      <p className="text-muted small mb-3">{session?.user.member_id}</p>

      {/* ---- Quick stats (total books, available, borrowed, overdue) ---- */}
      <div className="row g-3 mb-4">
        <StatCard icon="bi-book" label="Total Books" value={totalBooks} color="primary" />
        <StatCard icon="bi-check-circle" label={t('available')} value={availableBooks} color="success" />
        <StatCard icon="bi-bookmark" label="Books Borrowed" value={borrowedCount} color="info" />
        <StatCard icon="bi-exclamation-circle" label="Overdue" value={overdueCount} color="danger" />
      </div>

      <ul className="nav nav-pills mb-3">
        {(
          [
            ['loans', 'My Loans'],
            ['search', t('search')],
            ['leaderboard', 'NILAM Leaderboard'],
          ] as const
        ).map(([k, label]) => (
          <li className="nav-item" key={k}>
            <button className={`nav-link ${tab === k ? 'active' : ''}`} onClick={() => setTab(k)}>
              {label}
            </button>
          </li>
        ))}
      </ul>

      {tab === 'loans' && (
        <div className="card shadow-sm">
          <table className="table mb-0 align-middle">
            <thead className="table-light">
              <tr>
                <th>{t('title')}</th>
                <th>Due date</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {loanItems.map((loan) => {
                const badge = loanBadge(loan)
                return (
                  <tr key={loan.id}>
                    <td>{loan.copy?.book?.title || loan.copy?.accession_number}</td>
                    <td>{loan.due_date?.slice(0, 10)}</td>
                    <td>
                      <span className={`badge ${badge.className}`}>{badge.label}</span>
                    </td>
                  </tr>
                )
              })}
              {loanItems.length === 0 && (
                <tr>
                  <td colSpan={3} className="text-center text-muted py-4">
                    No active loans
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'search' && (
        <>
          <form
            className="d-flex gap-2 mb-3"
            onSubmit={(e) => {
              e.preventDefault()
              setSubmitted(query)
            }}
          >
            <input
              className="form-control"
              placeholder={t('searchPlaceholder')}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button className="btn btn-primary">{t('search')}</button>
          </form>
          <div className="row g-3">
            {bookItems.map((book) => (
              <div className="col-md-4" key={book.id}>
                <div className="card shadow-sm h-100">
                  <div className="card-body">
                    <Link to={`/catalog/${book.id}`} className="fw-semibold text-decoration-none">
                      {book.title}
                    </Link>
                    <div className="text-muted small">{book.author}</div>
                    <span className={`badge mt-2 ${(book.available_copies ?? 0) > 0 ? 'bg-success' : 'bg-secondary'}`}>
                      {(book.available_copies ?? 0) > 0 ? t('available') : 'On loan'}
                    </span>
                  </div>
                </div>
              </div>
            ))}
            {submitted && bookItems.length === 0 && <div className="text-muted">No results</div>}
          </div>
        </>
      )}

      {tab === 'leaderboard' && (
        <div className="row g-4">
          {/* Form filter - narrows both the class and student rankings below. */}
          <div className="col-12">
            <div className="d-flex align-items-center gap-2">
              <label className="form-label mb-0 fw-semibold">Form</label>
              <select
                className="form-select w-auto"
                value={form}
                onChange={(e) => setForm(e.target.value ? Number(e.target.value) : '')}
              >
                <option value="">All forms</option>
                {forms.map((f) => (
                  <option key={f} value={f}>
                    Form {f}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Per-class leaderboard (which class reads the most). */}
          <div className="col-lg-5">
            <div className="card shadow-sm h-100">
              <div className="card-header bg-transparent fw-semibold">Top Classes</div>
              <table className="table mb-0 align-middle">
                <thead className="table-light">
                  <tr>
                    <th style={{ width: 60 }}>#</th>
                    <th>Class</th>
                    <th className="text-end">Books read</th>
                  </tr>
                </thead>
                <tbody>
                  {topClasses.map((c, i) => (
                    <tr key={`${c.form_level}-${c.class_group}-${i}`}>
                      <td>{i + 1}</td>
                      <td>
                        Form {c.form_level} {c.class_group}
                      </td>
                      <td className="text-end fw-bold">{c.borrow_count ?? 0}</td>
                    </tr>
                  ))}
                  {topClasses.length === 0 && (
                    <tr>
                      <td colSpan={3} className="text-center text-muted py-4">
                        No data
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Individual student ranking. */}
          <div className="col-lg-7">
            <div className="card shadow-sm h-100">
              <div className="card-header bg-transparent fw-semibold">Top Students</div>
              <table className="table mb-0 align-middle">
                <thead className="table-light">
                  <tr>
                    <th style={{ width: 60 }}>#</th>
                    <th>Student</th>
                    <th>Class</th>
                    <th className="text-end">Books read</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((row, i) => (
                    <tr key={row.member_id || i}>
                      <td>{row.rank ?? i + 1}</td>
                      <td>{row.full_name}</td>
                      <td className="text-muted small">
                        {row.form_level ? `Form ${row.form_level} ${row.class_group ?? ''}` : ''}
                      </td>
                      <td className="text-end fw-bold">{row.borrow_count ?? 0}</td>
                    </tr>
                  ))}
                  {students.length === 0 && (
                    <tr>
                      <td colSpan={4} className="text-center text-muted py-4">
                        No data
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
