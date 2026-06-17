import { useState } from 'react'
import { Link } from 'react-router-dom'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap, type Pagination } from '../../api/client'
import type { Book } from '../../types'

/** GET /api/student/search - paginated book results + the category list. */
interface SearchData {
  items: Book[]
  pagination: Pagination
  categories: string[]
}

/**
 * Student "Search Books" page - a customer-friendly card grid (mirrors the
 * Flask student/search.html), kept deliberately more visual than the dense
 * staff catalog table. Browse by keyword, category, or availability.
 */
export default function StudentSearchPage() {
  const { t } = useTranslation()

  // `input` is what the user types; `search` is the submitted term we query on.
  const [input, setInput] = useState('')
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [availableOnly, setAvailableOnly] = useState(false)
  const [page, setPage] = useState(1)

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['student-search', search, category, availableOnly, page],
    queryFn: () =>
      unwrap<SearchData>(
        api.get('/api/student/search', {
          params: {
            page,
            per_page: 12,
            ...(search && { search }),
            ...(category && { category }),
            ...(availableOnly && { available: '1' }),
          },
        }),
      ),
    placeholderData: keepPreviousData,
  })

  const books = data?.items ?? []
  const categories = data?.categories ?? []
  const pg = data?.pagination

  function submit(e: React.FormEvent) {
    e.preventDefault()
    setSearch(input)
    setPage(1)
  }

  return (
    <div>
      <h4 className="mb-3">
        <i className="bi bi-search me-2" />
        {t('searchBooks')}
      </h4>

      {/* ---- Filters ---- */}
      <div className="card shadow-sm mb-4">
        <div className="card-header bg-light">
          <i className="bi bi-funnel me-2" />
          {t('filters')}
        </div>
        <div className="card-body">
          <form className="row g-3 align-items-end" onSubmit={submit}>
            <div className="col-12 col-lg-5">
              <label className="form-label fw-semibold">{t('search')}</label>
              <input
                className="form-control"
                placeholder={t('searchPlaceholder')}
                value={input}
                onChange={(e) => setInput(e.target.value)}
              />
            </div>
            <div className="col-12 col-md-6 col-lg-3">
              <label className="form-label fw-semibold">{t('category')}</label>
              <select
                className="form-select"
                value={category}
                onChange={(e) => {
                  setCategory(e.target.value)
                  setPage(1)
                }}
              >
                <option value="">{t('allCategories')}</option>
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-6 col-md-3 col-lg-2">
              <div className="form-check">
                <input
                  id="availOnly"
                  type="checkbox"
                  className="form-check-input"
                  checked={availableOnly}
                  onChange={(e) => {
                    setAvailableOnly(e.target.checked)
                    setPage(1)
                  }}
                />
                <label htmlFor="availOnly" className="form-check-label">
                  {t('availableOnly')}
                </label>
              </div>
            </div>
            <div className="col-6 col-md-3 col-lg-2">
              <button className="btn btn-primary w-100">
                <i className="bi bi-search me-1" />
                {t('search')}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* ---- Results ---- */}
      {isLoading ? (
        <div className="text-muted py-5 text-center">{t('loading')}</div>
      ) : books.length === 0 ? (
        <div className="alert alert-info text-center py-5">
          <i className="bi bi-search display-1 text-muted d-block mb-2" />
          <h5>{t('noBooksFound')}</h5>
          <p className="text-muted mb-0">{t('tryDifferentSearch')}</p>
        </div>
      ) : (
        <>
          <div className="row g-3 g-md-4" style={{ opacity: isFetching ? 0.6 : 1 }}>
            {books.map((book) => {
              const available = book.available_copies ?? 0
              return (
                <div className="col-6 col-md-4 col-lg-3" key={book.id}>
                  <div className="card book-card h-100 shadow-sm">
                    <div className="card-body d-flex flex-column">
                      <h6 className="card-title mb-1">
                        <Link to={`/catalog/${book.id}`} className="text-decoration-none">
                          {book.title}
                        </Link>
                      </h6>
                      <p className="text-muted small mb-2">{book.author || '—'}</p>
                      <div className="mb-2">
                        <span className="badge bg-light text-dark">{book.category || t('category')}</span>
                      </div>
                      <div className="mb-3 mt-auto">
                        {available > 0 ? (
                          <span className="badge bg-success">
                            {available}/{book.total_copies ?? available} {t('available')}
                          </span>
                        ) : (
                          <span className="badge bg-secondary">{t('notAvailable')}</span>
                        )}
                      </div>
                      <Link to={`/catalog/${book.id}`} className="btn btn-sm btn-outline-primary w-100">
                        {t('viewDetails')}
                      </Link>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* ---- Pagination ---- */}
          {pg && pg.total_pages > 1 && (
            <nav className="d-flex justify-content-center align-items-center gap-3 mt-4">
              <button
                className="btn btn-outline-primary btn-sm"
                disabled={!pg.has_prev}
                onClick={() => setPage((p) => p - 1)}
              >
                ‹ {t('previous')}
              </button>
              <span className="small text-muted">
                {pg.page} / {pg.total_pages}
              </span>
              <button
                className="btn btn-outline-primary btn-sm"
                disabled={!pg.has_next}
                onClick={() => setPage((p) => p + 1)}
              >
                {t('next')} ›
              </button>
            </nav>
          )}
        </>
      )}
    </div>
  )
}
