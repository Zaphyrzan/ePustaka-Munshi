import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../api/client'
import { useAuth } from '../auth/AuthContext'

interface DashboardStats {
  total_books: number
  total_copies: number
  available_copies: number
  total_members: number
  active_loans: number
  overdue_loans: number
  pending_ocr_jobs: number
}
interface Activity {
  type: 'checkout' | 'return'
  date: string | null
  book: string
  member: string
  staff_name: string
  status: string
  is_overdue: boolean
}
interface OverdueItem {
  id: number
  book: string
  member: string
  days_overdue: number
}
interface DashboardData {
  stats: DashboardStats
  activity: Activity[]
  overdue: OverdueItem[]
}

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

function fmtDate(iso: string | null) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function DashboardPage() {
  const { session } = useAuth()
  const { t } = useTranslation()

  const { data, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => unwrap<DashboardData>(api.get('/api/circulation/dashboard')),
    staleTime: 60_000,
  })

  return (
    <div>
      <h3 className="mb-1">{t('dashboard')}</h3>
      <p className="text-muted">
        {t('welcomeBack')}, {session?.user.full_name || session?.user.username}
      </p>

      {isLoading || !data ? (
        <div className="text-muted py-5 text-center">{t('loading')}</div>
      ) : (
        <>
          <div className="row g-4 mb-4">
            <StatCard icon="bi-book" label="Total Books" value={data.stats.total_books} color="primary" />
            <StatCard
              icon="bi-check-circle"
              label="Available Copies"
              value={`${data.stats.available_copies} / ${data.stats.total_copies}`}
              color="success"
            />
            <StatCard icon="bi-people" label="Active Members" value={data.stats.total_members} color="info" />
            <StatCard icon="bi-arrow-left-right" label={t('activeLoans')} value={data.stats.active_loans} color="warning" />
          </div>

          <div className="row g-4">
            {/* Recent Activity */}
            <div className="col-lg-8">
              <div className="card">
                <div className="card-header bg-transparent d-flex justify-content-between align-items-center">
                  <h6 className="mb-0">Recent Activity</h6>
                  <Link to="/circulation" className="btn btn-sm btn-outline-primary">
                    View All
                  </Link>
                </div>
                <div className="card-body p-0">
                  <div className="table-responsive">
                    <table className="table table-hover mb-0">
                      <thead className="table-light">
                        <tr>
                          <th>Action</th>
                          <th>Book</th>
                          <th>Member</th>
                          <th>Handled By</th>
                          <th>Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.activity.map((a, i) => (
                          <tr key={i}>
                            <td>
                              <span className={`badge ${a.type === 'checkout' ? 'bg-primary' : 'bg-success'}`}>
                                {a.type === 'checkout' ? 'Checkout' : 'Return'}
                              </span>
                            </td>
                            <td>{a.book.length > 40 ? a.book.slice(0, 40) + '…' : a.book}</td>
                            <td>{a.member}</td>
                            <td>
                              <strong>{a.staff_name}</strong>
                            </td>
                            <td className="text-muted small">{fmtDate(a.date)}</td>
                          </tr>
                        ))}
                        {data.activity.length === 0 && (
                          <tr>
                            <td colSpan={5} className="text-center text-muted py-4">
                              No recent activity
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>

            {/* Overdue + Quick Actions */}
            <div className="col-lg-4">
              {data.stats.overdue_loans > 0 && (
                <div className="card border-danger mb-4">
                  <div className="card-header bg-danger text-white">
                    <i className="bi bi-exclamation-triangle me-1" /> Overdue Books: {data.stats.overdue_loans}
                  </div>
                  <div className="card-body">
                    <ul className="list-unstyled mb-3">
                      {data.overdue.slice(0, 5).map((o) => (
                        <li key={o.id} className="py-2 border-bottom">
                          <strong>{o.book.length > 30 ? o.book.slice(0, 30) + '…' : o.book}</strong>
                          <br />
                          <small className="text-muted">
                            {o.member} — {o.days_overdue} days overdue
                          </small>
                        </li>
                      ))}
                    </ul>
                    <Link to="/circulation" className="btn btn-sm btn-outline-danger w-100">
                      View All Overdue
                    </Link>
                  </div>
                </div>
              )}

              <div className="card">
                <div className="card-header bg-transparent">
                  <h6 className="mb-0">Quick Actions</h6>
                </div>
                <div className="card-body">
                  <div className="d-grid gap-2">
                    <Link to="/circulation/checkout" className="btn btn-primary">
                      <i className="bi bi-box-arrow-right me-1" /> Checkout Book
                    </Link>
                    <Link to="/circulation/return" className="btn btn-success">
                      <i className="bi bi-box-arrow-in-left me-1" /> Return Book
                    </Link>
                    <Link to="/catalog/add" className="btn btn-outline-secondary">
                      <i className="bi bi-plus-circle me-1" /> Add New Book
                    </Link>
                    <Link to="/users/members/add" className="btn btn-outline-secondary">
                      <i className="bi bi-person-plus me-1" /> Add New Member
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
