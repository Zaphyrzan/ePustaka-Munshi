import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { API_BASE, api, unwrap } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import type { Book, BookCopy } from '../../types'

export default function BookDetailPage() {
  const { bookId } = useParams()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { session } = useAuth()
  const isStaff = session?.user_type === 'staff'

  const [showAddCopy, setShowAddCopy] = useState(false)
  const [copyForm, setCopyForm] = useState({ condition: 'Good', location: '', notes: '' })

  const { data, isLoading } = useQuery({
    queryKey: ['book', bookId],
    queryFn: () => unwrap<{ book: Book; copies: BookCopy[] }>(api.get(`/api/catalog/books/${bookId}`)),
  })

  const addCopy = useMutation({
    mutationFn: () => unwrap(api.post(`/api/catalog/books/${bookId}/copies`, copyForm)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['book', bookId] })
      setShowAddCopy(false)
      setCopyForm({ condition: 'Good', location: '', notes: '' })
    },
  })

  const deleteBook = useMutation({
    mutationFn: () => unwrap(api.delete(`/api/catalog/books/${bookId}`)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['books'] })
      navigate('/catalog')
    },
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
          <div className="d-flex justify-content-between align-items-start">
            <div>
              <h4 className="mb-1">{book.title}</h4>
              <p className="text-muted mb-3">{book.author}</p>
            </div>
            {isStaff && (
              <div className="d-flex gap-2">
                <Link to={`/catalog/${book.id}/edit`} className="btn btn-outline-primary btn-sm">
                  <i className="bi bi-pencil me-1" />
                  Edit
                </Link>
                <a
                  href={`${API_BASE}/catalog/book/${book.id}/print-barcodes`}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-outline-secondary btn-sm"
                >
                  <i className="bi bi-printer me-1" />
                  Print barcodes
                </a>
                <button
                  className="btn btn-outline-danger btn-sm"
                  onClick={() => {
                    if (confirm(`Delete "${book.title}" and all its copies?`)) deleteBook.mutate()
                  }}
                >
                  <i className="bi bi-trash me-1" />
                  Delete
                </button>
              </div>
            )}
          </div>
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

      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="mb-0">
          {t('copies')} ({copies.length})
        </h5>
        {isStaff && (
          <button className="btn btn-success btn-sm" onClick={() => setShowAddCopy((v) => !v)}>
            <i className={`bi ${showAddCopy ? 'bi-x-lg' : 'bi-plus-lg'} me-1`} />
            {showAddCopy ? 'Cancel' : 'Add copy'}
          </button>
        )}
      </div>

      {isStaff && showAddCopy && (
        <div className="card mb-3">
          <div className="card-body">
            <p className="small text-muted mb-3">
              <i className="bi bi-info-circle me-1" />
              Accession number and barcode are generated automatically.
            </p>
            <div className="row g-2 align-items-end">
              <div className="col-md-3">
                <label className="form-label small">Condition</label>
                <select
                  className="form-select"
                  value={copyForm.condition}
                  onChange={(e) => setCopyForm({ ...copyForm, condition: e.target.value })}
                >
                  <option>Good</option>
                  <option>Fair</option>
                  <option>Poor</option>
                </select>
              </div>
              <div className="col-md-4">
                <label className="form-label small">Shelf Location</label>
                <input
                  className="form-control"
                  placeholder="e.g. Shelf A-3"
                  value={copyForm.location}
                  onChange={(e) => setCopyForm({ ...copyForm, location: e.target.value })}
                />
              </div>
              <div className="col-md-3">
                <label className="form-label small">Notes</label>
                <input
                  className="form-control"
                  value={copyForm.notes}
                  onChange={(e) => setCopyForm({ ...copyForm, notes: e.target.value })}
                />
              </div>
              <div className="col-md-2">
                <button className="btn btn-primary w-100" onClick={() => addCopy.mutate()} disabled={addCopy.isPending}>
                  {addCopy.isPending ? t('loading') : 'Add'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <table className="table mb-0 align-middle">
          <thead className="table-light">
            <tr>
              <th>Accession #</th>
              <th>Barcode</th>
              <th>Status</th>
              <th>Condition</th>
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
                <td>{copy.condition || '—'}</td>
                <td>{copy.location || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
