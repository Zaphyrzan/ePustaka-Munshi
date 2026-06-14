import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap, type Paginated } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import type { Book } from '../../types'

export default function CatalogListPage() {
  const { t } = useTranslation()
  const { session } = useAuth()
  const [params, setParams] = useSearchParams()
  const page = Number(params.get('page') || 1)
  const search = params.get('search') || ''
  const category = params.get('category') || ''
  const availableOnly = params.get('available') === '1'
  const [searchInput, setSearchInput] = useState(search)

  // Update one or more query params, always resetting to page 1
  function update(next: Record<string, string>) {
    const merged: Record<string, string> = {}
    if (search) merged.search = search
    if (category) merged.category = category
    if (availableOnly) merged.available = '1'
    Object.assign(merged, next)
    Object.keys(merged).forEach((k) => merged[k] === '' && delete merged[k])
    setParams(merged)
  }

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: () => unwrap<string[]>(api.get('/api/catalog/categories')),
    staleTime: 5 * 60_000,
  })

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['books', page, search, category, availableOnly],
    queryFn: () =>
      unwrap<Paginated<Book>>(
        api.get('/api/catalog/books', {
          params: {
            page,
            per_page: 20,
            search,
            ...(category && { category }),
            ...(availableOnly && { available_only: 'true' }),
          },
        }),
      ),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  })

  function submitSearch(e: React.FormEvent) {
    e.preventDefault()
    update({ search: searchInput, page: '1' })
  }

  const pg = data?.pagination

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
        <h3 className="mb-0">
          {t('catalog')}{' '}
          {pg && <span className="fs-6 text-muted">({t('booksCount', { count: pg.total })})</span>}
        </h3>
        {session?.user_type === 'staff' && (
          <Link to="/catalog/add" className="btn btn-success text-nowrap">
            <i className="bi bi-plus-lg me-1" />
            {t('addBook')}
          </Link>
        )}
      </div>

      {/* Filters */}
      <div className="card mb-3">
        <div className="card-body d-flex flex-wrap gap-2 align-items-center">
          <form className="d-flex gap-2 flex-grow-1" onSubmit={submitSearch} style={{ minWidth: 240, maxWidth: 420 }}>
            <input
              className="form-control"
              placeholder={t('searchPlaceholder')}
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
            <button className="btn btn-primary">
              <i className="bi bi-search" />
            </button>
          </form>
          <select
            className="form-select"
            style={{ width: 200 }}
            value={category}
            onChange={(e) => update({ category: e.target.value, page: '1' })}
          >
            <option value="">{t('allCategories')}</option>
            {categories?.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <div className="form-check">
            <input
              id="availOnly"
              type="checkbox"
              className="form-check-input"
              checked={availableOnly}
              onChange={(e) => update({ available: e.target.checked ? '1' : '', page: '1' })}
            />
            <label htmlFor="availOnly" className="form-check-label">
              {t('availableOnly')}
            </label>
          </div>
          {(search || category || availableOnly) && (
            <button
              className="btn btn-outline-secondary btn-sm"
              onClick={() => {
                setSearchInput('')
                setParams({})
              }}
            >
              {t('clear')}
            </button>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="text-muted py-5 text-center">{t('loading')}</div>
      ) : (
        <>
          <div className="card">
            <table className="table table-hover mb-0 align-middle">
              <thead className="table-light">
                <tr>
                  <th>{t('title')}</th>
                  <th>{t('author')}</th>
                  <th>{t('category')}</th>
                  <th>{t('callNo')}</th>
                  <th className="text-center">{t('copies')}</th>
                  <th className="text-center">{t('available')}</th>
                </tr>
              </thead>
              <tbody style={{ opacity: isFetching ? 0.6 : 1 }}>
                {data?.items.map((book) => (
                  <tr key={book.id}>
                    <td>
                      <Link to={`/catalog/${book.id}`} className="fw-semibold text-decoration-none">
                        {book.title}
                      </Link>
                    </td>
                    <td>{book.author || '—'}</td>
                    <td>{book.category ? <span className="badge bg-light text-dark">{book.category}</span> : '—'}</td>
                    <td className="text-muted small">{book.call_number || '—'}</td>
                    <td className="text-center">{book.total_copies ?? '—'}</td>
                    <td className="text-center">
                      <span className={`badge ${(book.available_copies ?? 0) > 0 ? 'bg-success' : 'bg-secondary'}`}>
                        {book.available_copies ?? 0}
                      </span>
                    </td>
                  </tr>
                ))}
                {data?.items.length === 0 && (
                  <tr>
                    <td colSpan={6} className="text-center text-muted py-4">
                      {t('noBooksFound')}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {pg && pg.total_pages > 1 && (
            <nav className="d-flex justify-content-center mt-3 gap-2">
              <button className="btn btn-outline-primary btn-sm" disabled={!pg.has_prev} onClick={() => update({ page: String(page - 1) })}>
                ‹
              </button>
              <span className="align-self-center small text-muted">
                {pg.page} / {pg.total_pages}
              </span>
              <button className="btn btn-outline-primary btn-sm" disabled={!pg.has_next} onClick={() => update({ page: String(page + 1) })}>
                ›
              </button>
            </nav>
          )}
        </>
      )}
    </div>
  )
}
