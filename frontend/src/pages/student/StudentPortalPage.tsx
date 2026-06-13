import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { loanBadge, type Book, type Loan } from '../../types'

interface LeaderboardEntry {
  member_id?: string
  full_name?: string
  borrow_count?: number
  rank?: number
}

/** Student-facing portal: my loans, search, NILAM leaderboard */
export default function StudentPortalPage() {
  const { session } = useAuth()
  const { t } = useTranslation()
  const [tab, setTab] = useState<'loans' | 'search' | 'leaderboard'>('loans')
  const [query, setQuery] = useState('')
  const [submitted, setSubmitted] = useState('')

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

  const { data: leaderboard } = useQuery({
    queryKey: ['leaderboard'],
    queryFn: () => unwrap<{ top_students?: LeaderboardEntry[] }>(api.get('/api/student/leaderboard')),
    enabled: tab === 'leaderboard',
  })

  const loanItems: Loan[] = loans?.active?.items ?? []
  const bookItems: Book[] = Array.isArray(results) ? results : (results?.items ?? [])
  const lbItems: LeaderboardEntry[] = leaderboard?.top_students ?? []

  return (
    <div>
      <h4 className="mb-1">
        {t('welcomeBack')}, {session?.user.full_name}
      </h4>
      <p className="text-muted small mb-3">{session?.user.member_id}</p>

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
        <div className="card shadow-sm">
          <table className="table mb-0 align-middle">
            <thead className="table-light">
              <tr>
                <th style={{ width: 60 }}>#</th>
                <th>Student</th>
                <th className="text-end">Books read</th>
              </tr>
            </thead>
            <tbody>
              {lbItems.map((row, i) => (
                <tr key={row.member_id || i}>
                  <td>{row.rank ?? i + 1}</td>
                  <td>{row.full_name}</td>
                  <td className="text-end fw-bold">{row.borrow_count ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
