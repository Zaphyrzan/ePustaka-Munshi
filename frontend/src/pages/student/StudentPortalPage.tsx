import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { loanBadge, type Loan } from '../../types'

/** GET /api/student/dashboard - library stats + this member's current loans. */
interface DashboardData {
  stats: { total_books: number; available_copies: number; books_read: number }
  member: { active_loans?: number; overdue_loans?: number; class_group?: string } | null
  my_loans: Loan[]
  due_soon: Loan[]
  overdue: Loan[]
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

/**
 * Student home page (mirrors the Flask student/index.html dashboard):
 * quick stats, overdue/due-soon alerts, quick-access buttons and a short
 * "currently borrowed" list. My Loans and the Leaderboard are their own pages.
 */
export default function StudentPortalPage() {
  const { session } = useAuth()
  const { t } = useTranslation()

  const { data } = useQuery({
    queryKey: ['student-dashboard'],
    queryFn: () => unwrap<DashboardData>(api.get('/api/student/dashboard')),
  })

  const myLoans: Loan[] = data?.my_loans ?? []
  const overdue: Loan[] = data?.overdue ?? []
  const dueSoon: Loan[] = data?.due_soon ?? []

  const totalBooks = data?.stats.total_books ?? 0
  const availableBooks = data?.stats.available_copies ?? 0
  const overdueCount = data?.member?.overdue_loans ?? overdue.length
  // "Borrowed" = books currently out. An overdue book is still borrowed, so we
  // add active + overdue rather than showing active-only (which could read 0).
  const borrowedCount = (data?.member?.active_loans ?? 0) + overdueCount

  return (
    <div>
      <h4 className="mb-1">
        {t('welcomeBack')}, {session?.user.full_name}
      </h4>
      <p className="text-muted small mb-3">{session?.user.member_id}</p>

      {/* ---- Alerts for overdue / due-soon books ---- */}
      {overdueCount > 0 && (
        <div className="alert alert-danger d-flex align-items-center" role="alert">
          <i className="bi bi-exclamation-triangle-fill me-2" />
          <div>
            You have <strong>{overdueCount}</strong> overdue book{overdueCount === 1 ? '' : 's'}.{' '}
            <Link to="/student/loans" className="alert-link">
              View
            </Link>
          </div>
        </div>
      )}
      {dueSoon.length > 0 && (
        <div className="alert alert-warning d-flex align-items-center" role="alert">
          <i className="bi bi-info-circle-fill me-2" />
          <div>
            <strong>{dueSoon.length}</strong> book{dueSoon.length === 1 ? '' : 's'} due within 3 days.{' '}
            <Link to="/student/loans" className="alert-link">
              View
            </Link>
          </div>
        </div>
      )}

      {/* ---- Quick stats ---- */}
      <div className="row g-3 mb-4">
        <StatCard icon="bi-book" label="Total Books" value={totalBooks} color="primary" />
        <StatCard icon="bi-check-circle" label={t('available')} value={availableBooks} color="success" />
        <StatCard icon="bi-bookmark" label="Books Borrowed" value={borrowedCount} color="info" />
        <StatCard icon="bi-exclamation-circle" label="Overdue" value={overdueCount} color="danger" />
      </div>

      {/* ---- Quick access buttons ---- */}
      <div className="row g-3 mb-4">
        <div className="col-12 col-sm-4">
          <Link to="/catalog" className="btn btn-lg btn-primary w-100 py-3">
            <i className="bi bi-search me-2" />
            {t('search')}
          </Link>
        </div>
        <div className="col-12 col-sm-4">
          <Link to="/student/loans" className="btn btn-lg btn-outline-primary w-100 py-3">
            <i className="bi bi-journal-bookmark me-2" />
            My Loans
          </Link>
        </div>
        <div className="col-12 col-sm-4">
          <Link to="/student/leaderboard" className="btn btn-lg btn-outline-success w-100 py-3">
            <i className="bi bi-trophy me-2" />
            Leaderboard
          </Link>
        </div>
      </div>

      {/* ---- Currently borrowed (short list, full list on My Loans) ---- */}
      <h5 className="mb-3">
        <i className="bi bi-bookmark-check me-2" />
        Currently Borrowed
      </h5>
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
            {myLoans.slice(0, 5).map((loan) => {
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
            {myLoans.length === 0 && (
              <tr>
                <td colSpan={3} className="text-center text-muted py-4">
                  No books borrowed yet.{' '}
                  <Link to="/catalog">Borrow a book</Link>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {myLoans.length > 5 && (
        <div className="text-center mt-3">
          <Link to="/student/loans" className="btn btn-outline-primary btn-sm">
            View all
          </Link>
        </div>
      )}
    </div>
  )
}
