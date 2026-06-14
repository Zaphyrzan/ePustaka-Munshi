import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api, unwrap } from '../../api/client'
import { loanBadge, type Loan } from '../../types'

/** GET /api/student/loans - active (incl. overdue) loans plus returned history. */
interface LoansData {
  active?: { items?: Loan[] }
  history?: { items?: Loan[] }
}

/** Format an ISO date string as DD/MM/YYYY (or '-' when missing). */
function fmtDate(iso?: string) {
  if (!iso) return '-'
  const [y, m, d] = iso.slice(0, 10).split('-')
  return `${d}/${m}/${y}`
}

/**
 * My Loans page (mirrors the Flask student/my_loans.html):
 * summary cards, a table of the books currently borrowed, and the
 * history of books already returned.
 */
export default function StudentLoansPage() {
  const { data } = useQuery({
    queryKey: ['student-loans-full'],
    queryFn: () => unwrap<LoansData>(api.get('/api/student/loans')),
  })

  const active: Loan[] = data?.active?.items ?? []
  const history: Loan[] = data?.history?.items ?? []

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h4 className="mb-0">
          <i className="bi bi-journal-bookmark me-2" />
          My Loans
        </h4>
        <Link to="/student" className="btn btn-outline-secondary btn-sm">
          <i className="bi bi-arrow-left me-1" />
          Back
        </Link>
      </div>

      {/* ---- Summary cards ---- */}
      <div className="row g-3 mb-4">
        <div className="col-12 col-md-4">
          <div className="card border-0 shadow-sm bg-primary text-white h-100">
            <div className="card-body d-flex justify-content-between align-items-center">
              <div>
                <div className="opacity-75 small">Currently Borrowed</div>
                <div className="fs-2 fw-bold">{active.length}</div>
              </div>
              <i className="bi bi-journal-check fs-1 opacity-50" />
            </div>
          </div>
        </div>
        <div className="col-12 col-md-4">
          <div className="card border-0 shadow-sm bg-secondary text-white h-100">
            <div className="card-body d-flex justify-content-between align-items-center">
              <div>
                <div className="opacity-75 small">Returned</div>
                <div className="fs-2 fw-bold">{history.length}</div>
              </div>
              <i className="bi bi-clock-history fs-1 opacity-50" />
            </div>
          </div>
        </div>
        <div className="col-12 col-md-4">
          <div className="card border-0 shadow-sm bg-success text-white h-100">
            <div className="card-body d-flex justify-content-between align-items-center">
              <div>
                <div className="opacity-75 small">Total Loans</div>
                <div className="fs-2 fw-bold">{active.length + history.length}</div>
              </div>
              <i className="bi bi-graph-up fs-1 opacity-50" />
            </div>
          </div>
        </div>
      </div>

      {/* ---- Active loans ---- */}
      <div className="card shadow-sm mb-4">
        <div className="card-header bg-white d-flex justify-content-between align-items-center">
          <h5 className="mb-0">
            <i className="bi bi-journal-text me-2" />
            Books Borrowed
          </h5>
          <span className="badge bg-primary">{active.length} books</span>
        </div>
        <div className="table-responsive">
          <table className="table mb-0 align-middle">
            <thead className="table-light">
              <tr>
                <th>Book</th>
                <th>Accession #</th>
                <th>Loan date</th>
                <th>Due date</th>
                <th>Status</th>
                <th className="text-end">Days left</th>
              </tr>
            </thead>
            <tbody>
              {active.map((loan) => {
                const badge = loanBadge(loan)
                return (
                  <tr key={loan.id}>
                    <td>
                      <Link to={`/catalog/${loan.copy?.book?.id}`} className="text-decoration-none fw-semibold">
                        {loan.copy?.book?.title || loan.copy?.accession_number}
                      </Link>
                      <div className="text-muted small">{loan.copy?.book?.author}</div>
                    </td>
                    <td>
                      <code>{loan.copy?.accession_number}</code>
                    </td>
                    <td>{fmtDate(loan.loan_date)}</td>
                    <td className="fw-semibold">{fmtDate(loan.due_date)}</td>
                    <td>
                      <span className={`badge ${badge.className}`}>{badge.label}</span>
                    </td>
                    <td className="text-end">{loan.days_remaining ?? '-'}</td>
                  </tr>
                )
              })}
              {active.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center text-muted py-4">
                    No books borrowed.{' '}
                    <Link to="/catalog">Search books</Link>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ---- Loan history (returned books) ---- */}
      <div className="card shadow-sm">
        <div className="card-header bg-white">
          <h5 className="mb-0">
            <i className="bi bi-clock-history me-2" />
            Loan History
          </h5>
        </div>
        <div className="table-responsive">
          <table className="table mb-0 align-middle">
            <thead className="table-light">
              <tr>
                <th>Book</th>
                <th>Loan date</th>
                <th>Return date</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {history.map((loan) => (
                <tr key={loan.id}>
                  <td>
                    <Link to={`/catalog/${loan.copy?.book?.id}`} className="text-decoration-none">
                      {loan.copy?.book?.title || loan.copy?.accession_number}
                    </Link>
                    <div className="text-muted small">{loan.copy?.book?.author}</div>
                  </td>
                  <td>{fmtDate(loan.loan_date)}</td>
                  <td>{fmtDate(loan.return_date)}</td>
                  <td>
                    <span className="badge bg-secondary">
                      <i className="bi bi-check me-1" />
                      Returned
                    </span>
                  </td>
                </tr>
              ))}
              {history.length === 0 && (
                <tr>
                  <td colSpan={4} className="text-center text-muted py-4">
                    No loan history yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
