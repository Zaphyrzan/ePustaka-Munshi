import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../../api/client'
import type { Book, BookCopy } from '../../types'

const EMPTY = {
  title: '',
  author: '',
  isbn: '',
  publisher: '',
  publication_year: '',
  category: '',
  call_number: '',
  language: 'Malay',
  description: '',
  price: '',
}

/** Add (no :bookId) or edit (:bookId) a bibliographic record */
export default function BookFormPage() {
  const { bookId } = useParams()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!bookId) return
    unwrap<{ book: Book; copies: BookCopy[] }>(api.get(`/api/catalog/books/${bookId}`)).then(({ book }) =>
      setForm({
        title: book.title || '',
        author: book.author || '',
        isbn: book.isbn || '',
        publisher: book.publisher || '',
        publication_year: book.publication_year ? String(book.publication_year) : '',
        category: book.category || '',
        call_number: book.call_number || '',
        language: book.language || 'Malay',
        description: book.description || '',
        price: book.price != null ? String(book.price) : '',
      }),
    )
  }, [bookId])

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    const payload = {
      ...form,
      publication_year: form.publication_year ? Number(form.publication_year) : null,
      price: form.price ? Number(form.price) : null,
    }
    try {
      if (bookId) {
        await unwrap(api.put(`/api/catalog/books/${bookId}`, payload))
      } else {
        await unwrap(api.post('/api/catalog/books', payload))
      }
      queryClient.invalidateQueries({ queryKey: ['books'] })
      queryClient.invalidateQueries({ queryKey: ['book', bookId] })
      navigate('/catalog')
    } catch (err) {
      setError(err instanceof Error ? err.message : t('error'))
    } finally {
      setBusy(false)
    }
  }

  function field(label: string, key: keyof typeof EMPTY, props: Record<string, unknown> = {}) {
    return (
      <div className="col-md-6 mb-3">
        <label className="form-label">{label}</label>
        <input
          className="form-control"
          value={form[key]}
          onChange={(e) => setForm({ ...form, [key]: e.target.value })}
          {...props}
        />
      </div>
    )
  }

  return (
    <div className="mx-auto" style={{ maxWidth: 860 }}>
      <h4 className="mb-3">{bookId ? 'Edit Book' : 'Add Book'}</h4>
      {error && <div className="alert alert-danger py-2">{error}</div>}
      <form onSubmit={submit} className="card shadow-sm p-4">
        <div className="row">
          {field(t('title'), 'title', { required: true })}
          {field(t('author'), 'author')}
          {field('ISBN', 'isbn')}
          {field(t('publisher'), 'publisher')}
          {field(t('year'), 'publication_year', { type: 'number', min: 1800, max: 2100 })}
          {field(t('category'), 'category')}
          {field('Call Number', 'call_number')}
          <div className="col-md-6 mb-3">
            <label className="form-label">Language</label>
            <select
              className="form-select"
              value={form.language}
              onChange={(e) => setForm({ ...form, language: e.target.value })}
            >
              {['Malay', 'English', 'Chinese', 'Tamil', 'Arabic'].map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </select>
          </div>
          {field('Price (RM)', 'price', { type: 'number', step: '0.01', min: 0 })}
        </div>
        <div className="mb-3">
          <label className="form-label">Description</label>
          <textarea
            className="form-control"
            rows={3}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
        </div>
        <div className="d-flex gap-2">
          <button className="btn btn-primary" disabled={busy}>
            {busy ? t('loading') : bookId ? 'Save changes' : 'Add book'}
          </button>
          <button type="button" className="btn btn-outline-secondary" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
