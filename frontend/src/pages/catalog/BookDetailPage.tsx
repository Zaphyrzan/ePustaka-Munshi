import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../../api/client'
import type { Book, BookCopy } from '../../types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000'

export default function BookDetailPage() {
  const { bookId } = useParams()
  const { t } = useTranslation()

  const { data, isLoading } = useQuery({
    queryKey: ['book', bookId],
    queryFn: () => unwrap<{ book: Book; copies: BookCopy[] }>(api.get(`/api/catalog/books/${bookId}`)),
  })

  if (isLoading) return <div className="text-muted py-5 text-center">{t('loading')}</div>
  if (!data) return <div className="alert alert-warning">Book not found</div>

  const { book, copies } = data

  return (
    <div>
      <nav className="mb-3">
        <Link to="/catalog" className="text-decoration-none">
          ‹ {t('catalog')}
        </Link>
      </nav>

      <div className="card shadow-sm mb-4">
        <div className="card-body">
          <h4 className="mb-1">{book.title}</h4>
          <p className="text-muted mb-3">{book.author}</p>
          <div className="row small">
            <div className="col-md-3">
              <strong>{t('publisher')}:</strong> {book.publisher || '—'}
            </div>
            <div className="col-md-2">
              <strong>{t('year')}:</strong> {book.publication_year || '—'}
            </div>
            <div className="col-md-3">
              <strong>Call #:</strong> {book.call_number || '—'}
            </div>
            <div className="col-md-2">
              <strong>{t('category')}:</strong> {book.category || '—'}
            </div>
            <div className="col-md-2">
              <strong>ISBN:</strong> {book.isbn || '—'}
            </div>
          </div>
        </div>
      </div>

      <h5 className="mb-3">
        {t('copies')} ({copies.length})
      </h5>
      <div className="card shadow-sm">
        <table className="table mb-0 align-middle">
          <thead className="table-light">
            <tr>
              <th>Accession #</th>
              <th>Barcode</th>
              <th>Status</th>
              <th>Location</th>
            </tr>
          </thead>
          <tbody>
            {copies.map((copy) => (
              <tr key={copy.id}>
                <td>{copy.accession_number}</td>
                <td>
                  {copy.barcode ? (
                    <img
                      src={`${API_BASE}/catalog/api/barcode/${copy.barcode}`}
                      alt={copy.barcode}
                      style={{ height: 40 }}
                    />
                  ) : (
                    '—'
                  )}
                </td>
                <td>
                  <span className={`badge ${copy.status === 'available' ? 'bg-success' : 'bg-warning text-dark'}`}>
                    {copy.status}
                  </span>
                </td>
                <td>{copy.location || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
