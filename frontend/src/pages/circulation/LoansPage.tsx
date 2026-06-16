import { useState } from 'react'
import { Link } from 'react-router-dom'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap, type Paginated } from '../../api/client'
import { loanBadge, type Loan } from '../../types'
import SortHeader from '../../components/SortHeader'

type Tab = 'active' | 'overdue' | 'all'

export default function LoansPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<Tab>('active')
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState('checkout_date')
  const [order, setOrder] = useState<'asc' | 'desc'>('desc')

  function onSort(field: string) {
    if (sort === field) setOrder(order === 'asc' ? 'desc' : 'asc')
    else {
      setSort(field)
      setOrder('asc')
    }
    setPage(1)
  }

  const { data, isLoading } = useQuery({
    queryKey: ['loans', tab, page, sort, order],
    queryFn: () => {
      if (tab === 'overdue') {
        return unwrap<Paginated<Loan>>(api.get('/api/circulation/overdue', { params: { page, per_page: 15 } }))
      }
      const params: Record<string, unknown> = { page, per_page: 15, sort, order }
      if (tab === 'active') params.status = 'active'
      return unwrap<Paginated<Loan>>(api.get('/api/circulation/loans', { params }))
    },
    placeholderData: keepPreviousData,
  })

  const renew = useMutation({
    mutationFn: (loanId: number) => unwrap(api.post(`/api/circulation/loans/${loanId}/renew`, {})),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['loans'] }),
  })

  const pg = data?.pagination

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h4 className="mb-0">{t('circulation')}</h4>
        <div className="d-flex gap-2">
          <Link to="/circulation/checkout" className="btn btn-success">
            <i className="bi bi-box-arrow-right me-1" />
            {t('checkout')}
          </Link>
          <Link to="/circulation/return" className="btn btn-primary">
            <i className="bi bi-box-arrow-in-left me-1" />
            {t('return')}
          </Link>
        </div>
      </div>

      <ul className="nav nav-tabs mb-3">
        {(['active', 'overdue', 'all'] as Tab[]).map((k) => (
          <li className="nav-item" key={k}>
            <button
              className={`nav-link ${tab === k ? 'active' : ''}`}
              onClick={() => {
                setTab(k)
                setPage(1)
              }}
            >
              {k === 'active' ? t('activeLoans') : k === 'overdue' ? t('overdue') : t('history')}
            </button>
          </li>
        ))}
      </ul>

      {isLoading ? (
        <div className="text-muted py-5 text-center">{t('loading')}</div>
      ) : (
        <div className="card shadow-sm">
          <table className="table table-hover mb-0 align-middle">
            <thead className="table-light">
              <tr>
                {tab === 'overdue' ? (
                  <>
                    <th>{t('title')}</th>
                    <th>{t('member')}</th>
                    <th>{t('dueDate')}</th>
                    <th>{t('status')}</th>
                  </>
                ) : (
                  <>
                    <SortHeader label={t('title')} field="book" sort={sort} order={order} onSort={onSort} />
                    <SortHeader label={t('member')} field="member" sort={sort} order={order} onSort={onSort} />
                    <SortHeader label={t('dueDate')} field="due_date" sort={sort} order={order} onSort={onSort} />
                    <SortHeader label={t('status')} field="status" sort={sort} order={order} onSort={onSort} />
                  </>
                )}
                <th>{t('handledBy')}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data?.items.map((loan) => (
                <tr key={loan.id}>
                  <td>{loan.copy?.book?.title || loan.copy?.accession_number || '—'}</td>
                  <td>
                    {loan.member?.full_name}{' '}
                    <span className="text-muted small">({loan.member?.member_id})</span>
                  </td>
                  <td>{loan.due_date?.slice(0, 10) || '—'}</td>
                  <td>
                    <span className={`badge ${loanBadge(loan).className}`}>{loanBadge(loan).label}</span>
                  </td>
                  <td className="small">
                    <div>
                      <i className="bi bi-box-arrow-right text-primary me-1" />
                      {loan.checkout_staff?.full_name || 'System'}
                    </div>
                    {loan.return_date && (
                      <div className="text-success">
                        <i className="bi bi-box-arrow-in-left me-1" />
                        {loan.return_staff?.full_name || 'System'}
                      </div>
                    )}
                  </td>
                  <td className="text-end">
                    {(loan.status === 'active' || loan.status === 'overdue') && (
                      <button
                        className="btn btn-outline-primary btn-sm"
                        onClick={() => renew.mutate(loan.id)}
                        disabled={renew.isPending}
                      >
                        {t('renew')}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {data?.items.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center text-muted py-4">
                    {t('noLoans')}
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
