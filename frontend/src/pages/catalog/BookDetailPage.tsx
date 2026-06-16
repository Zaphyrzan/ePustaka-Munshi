import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../../api/client'
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
  const [editId, setEditId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState({ status: 'available', condition: 'Good', location: '', notes: '' })

  function startEdit(c: BookCopy) {
    setEditId(c.id)
    setEditForm({
      status: c.status || 'available',
      condition: c.condition || 'Good',
      location: c.location || '',
      notes: (c as BookCopy & { notes?: string }).notes || '',
    })
  }

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

  const updateCopy = useMutation({
    mutationFn: (id: number) => unwrap(api.put(`/api/catalog/copies/${id}`, editForm)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['book', bookId] })
      setEditId(null)
    },
  })

  const deleteCopy = useMutation({
    mutationFn: (id: number) => unwrap(api.delete(`/api/catalog/copies/${id}`)),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['book', bookId] }),
    onError: (err) => alert(err instanceof Error ? err.message : 'Could not delete copy'),
  })

  const COPY_STATUSES = ['available', 'on_loan', 'reserved', 'lost', 'damaged', 'withdrawn']

  if (isLoading) return <div className="text-muted py-5 text-center">{t('loading')}</div>
  if (!data) return <div className="alert alert-warning">{t('bookNotFound')}</div>

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
                  {t('edit')}
                </Link>
                <Link to={`/catalog/${book.id}/print-barcodes`} className="btn btn-outline-secondary btn-sm">
                  <i className="bi bi-printer me-1" />
                  {t('printBarcodes')}
                </Link>
                <button
                  className="btn btn-outline-danger btn-sm"
                  onClick={() => {
                    if (confirm(`Delete "${book.title}" and all its copies?`)) deleteBook.mutate()
                  }}
                >
                  <i className="bi bi-trash me-1" />
                  {t('delete')}
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
              <strong>{t('callNo')}:</strong> {book.call_number || '—'}
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
            {showAddCopy ? t('cancel') : t('addCopy')}
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
              <th>{t('accessionNo')}</th>
              <th>{t('barcode')}</th>
              <th>{t('status')}</th>
              <th>{t('condition')}</th>
              <th>{t('location')}</th>
              {isStaff && <th className="text-end">{t('actions')}</th>}
            </tr>
          </thead>
          <tbody>
            {copies.map((copy) =>
              editId === copy.id ? (
                <tr key={copy.id} className="table-warning">
                  <td>{copy.accession_number}</td>
                  <td className="font-monospace">{copy.barcode || '—'}</td>
                  <td>
                    <select
                      className="form-select form-select-sm"
                      value={editForm.status}
                      onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                    >
                      {COPY_STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <select
                      className="form-select form-select-sm"
                      value={editForm.condition}
                      onChange={(e) => setEditForm({ ...editForm, condition: e.target.value })}
                    >
                      <option>Good</option>
                      <option>Fair</option>
                      <option>Poor</option>
                    </select>
                  </td>
                  <td>
                    <input
                      className="form-control form-control-sm"
                      placeholder="Shelf"
                      value={editForm.location}
                      onChange={(e) => setEditForm({ ...editForm, location: e.target.value })}
                    />
                  </td>
                  <td className="text-end text-nowrap">
                    <button
                      className="btn btn-success btn-sm me-1"
                      onClick={() => updateCopy.mutate(copy.id)}
                      disabled={updateCopy.isPending}
                    >
                      {t('save')}
                    </button>
                    <button className="btn btn-outline-secondary btn-sm" onClick={() => setEditId(null)}>
                      {t('cancel')}
                    </button>
                  </td>
                </tr>
              ) : (
                <tr key={copy.id}>
                  <td>{copy.accession_number}</td>
                  <td className="font-monospace">{copy.barcode || '—'}</td>
                  <td>
                    <span className={`badge ${copy.status === 'available' ? 'bg-success' : 'bg-warning text-dark'}`}>
                      {copy.status}
                    </span>
                  </td>
                  <td>{copy.condition || '—'}</td>
                  <td>{copy.location || '—'}</td>
                  {isStaff && (
                    <td className="text-end text-nowrap">
                      <button className="btn btn-outline-primary btn-sm me-1" onClick={() => startEdit(copy)}>
                        <i className="bi bi-pencil" />
                      </button>
                      <button
                        className="btn btn-outline-danger btn-sm"
                        title="Delete copy"
                        onClick={() => {
                          if (confirm(`Delete copy ${copy.accession_number}? This cannot be undone.`))
                            deleteCopy.mutate(copy.id)
                        }}
                      >
                        <i className="bi bi-trash" />
                      </button>
                    </td>
                  )}
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
