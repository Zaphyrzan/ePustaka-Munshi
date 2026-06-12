import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap, type Paginated } from '../../api/client'
import type { Book } from '../../types'

export default function CatalogListPage() {
  const { t } = useTranslation()
  const [params, setParams] = useSearchParams()
  const page = Number(params.get('page') || 1)
  const search = params.get('search') || ''
  const [searchInput, setSearchInput] = useState(search)

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['books', page, search],
    queryFn: () =>
      unwrap<Paginated<Book>>(
        api.get('/api/catalog/books', { params: { page, per_page: 20, search } }),
      ),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  })

  function submitSearch(e: React.FormEvent) {
    e.preventDefault()
    setParams(searchInput ? { search: searchInput } : {})
  }

  const pg = data?.pagination

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h3 className="mb-0">
          {t('catalog')}{' '}
          {pg && <span className="fs-6 text-muted">({pg.total.toLocaleString()} {t('title').toLowerCase()}s)</span>}
        </h3>
        <form className="d-flex gap-2" onSubmit={submitSearch} style={{ width: 420 }}>
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
      </div>

      {isLoading ? (
        <div className="text-muted py-5 text-center">{t('loading')}</div>
      ) : (
        <>
          <div className="card shadow-sm">
            <table className="table table-hover mb-0 align-middle">
              <thead className="table-light">
                <tr>
                  <th>{t('title')}</th>
                  <th>{t('author')}</th>
                  <th>{t('publisher')}</th>
                  <th className="text-center">{t('year')}</th>
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
                    <td>{book.publisher || '—'}</td>
                    <td className="text-center">{book.publication_year || '—'}</td>
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
                      No books found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {pg && pg.total_pages > 1 && (
            <nav className="d-flex justify-content-center mt-3 gap-2">
              <button
                className="btn btn-outline-primary btn-sm"
                disabled={!pg.has_prev}
                onClick={() => setParams({ ...(search && { search }), page: String(page - 1) })}
              >
                ‹
              </button>
              <span className="align-self-center small text-muted">
                {pg.page} / {pg.total_pages}
              </span>
              <button
                className="btn btn-outline-primary btn-sm"
                disabled={!pg.has_next}
                onClick={() => setParams({ ...(search && { search }), page: String(page + 1) })}
              >
                ›
              </button>
            </nav>
          )}
        </>
      )}
    </div>
  )
}
