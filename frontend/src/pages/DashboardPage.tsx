import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap, type Paginated } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Book, CirculationStats } from '../types'

function StatCard({ icon, label, value, color }: { icon: string; label: string; value: number | string; color: string }) {
  return (
    <div className="col-md-3 col-sm-6">
      <div className="card shadow-sm h-100">
        <div className="card-body d-flex align-items-center gap-3">
          <i className={`bi ${icon} fs-1 text-${color}`} />
          <div>
            <div className="fs-3 fw-bold">{value}</div>
            <div className="text-muted small">{label}</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const { session } = useAuth()
  const { t } = useTranslation()

  const { data: stats, isLoading } = useQuery({
    queryKey: ['circulation-stats'],
    queryFn: () => unwrap<CirculationStats>(api.get('/api/circulation/stats')),
    staleTime: 60_000,
  })

  // Stats endpoint covers loans only; book totals come from catalog pagination
  const { data: bookTotals } = useQuery({
    queryKey: ['book-totals'],
    queryFn: async () => {
      const all = await unwrap<Paginated<Book>>(api.get('/api/catalog/books', { params: { per_page: 1 } }))
      const avail = await unwrap<Paginated<Book>>(
        api.get('/api/catalog/books', { params: { per_page: 1, available_only: true } }),
      )
      return { total: all.pagination.total, available: avail.pagination.total }
    },
    staleTime: 60_000,
  })

  return (
    <div>
      <h3 className="mb-1">{t('dashboard')}</h3>
      <p className="text-muted">
        {t('welcomeBack')}, {session?.user.full_name || session?.user.username}
      </p>
      {isLoading ? (
        <div className="text-muted">{t('loading')}</div>
      ) : (
        <div className="row g-3">
          <StatCard icon="bi-journal-bookmark" label={t('catalog')} value={bookTotals?.total ?? '—'} color="primary" />
          <StatCard icon="bi-check-circle" label={t('available')} value={bookTotals?.available ?? '—'} color="success" />
          <StatCard icon="bi-arrow-left-right" label={t('activeLoans')} value={stats?.active_loans ?? '—'} color="info" />
          <StatCard icon="bi-exclamation-triangle" label={t('overdue')} value={stats?.overdue_loans ?? '—'} color="danger" />
        </div>
      )}
    </div>
  )
}
