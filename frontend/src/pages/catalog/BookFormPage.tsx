import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../../api/client'
import type { Book, BookCopy } from '../../types'

/** Curated default categories for a Malaysian school library. */
const CURATED_CATEGORIES = [
  'Fiction',
  'Non-Fiction',
  'Religion & Islamic Studies',
  'Science',
  'Mathematics',
  'Technology & Computing',
  'History',
  'Geography',
  'Language & Literature',
  'Poetry',
  'Reference',
  'Dictionary & Encyclopedia',
  'Biography',
  'Arts & Music',
  'Health & Sports',
  'Comics & Graphic Novels',
  'Magazines & Periodicals',
  'Textbook',
  "Children's Books",
  'Motivation & Self-Help',
]

const OTHERS = 'Others'

// Languages most relevant to a Malaysian school library, pinned to the top.
const COMMON_LANGUAGES = ['Malay', 'English', 'Chinese', 'Tamil', 'Arabic', 'Japanese']

// A broad set of standard world languages for everything else (alphabetical).
const OTHER_LANGUAGES = [
  'Afrikaans', 'Albanian', 'Amharic', 'Armenian', 'Azerbaijani', 'Basque', 'Belarusian',
  'Bengali', 'Bosnian', 'Bulgarian', 'Burmese', 'Catalan', 'Cebuano', 'Croatian', 'Czech',
  'Danish', 'Dutch', 'Esperanto', 'Estonian', 'Filipino', 'Finnish', 'French', 'Georgian',
  'German', 'Greek', 'Gujarati', 'Hausa', 'Hebrew', 'Hindi', 'Hungarian', 'Icelandic',
  'Igbo', 'Indonesian', 'Irish', 'Italian', 'Javanese', 'Kannada', 'Kazakh', 'Khmer',
  'Korean', 'Kurdish', 'Lao', 'Latin', 'Latvian', 'Lithuanian', 'Macedonian', 'Malagasy',
  'Malayalam', 'Maltese', 'Marathi', 'Mongolian', 'Nepali', 'Norwegian', 'Pashto',
  'Persian', 'Polish', 'Portuguese', 'Punjabi', 'Romanian', 'Russian', 'Serbian', 'Sinhala',
  'Slovak', 'Slovenian', 'Somali', 'Spanish', 'Swahili', 'Swedish', 'Tagalog', 'Telugu',
  'Thai', 'Tibetan', 'Turkish', 'Turkmen', 'Ukrainian', 'Urdu', 'Uzbek', 'Vietnamese',
  'Welsh', 'Yiddish', 'Yoruba', 'Zulu',
]

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
  const [otherCategory, setOtherCategory] = useState(false)

  const { data: existingCategories } = useQuery({
    queryKey: ['categories'],
    queryFn: () => unwrap<string[]>(api.get('/api/catalog/categories')),
  })

  // Curated list + any categories already in the DB, de-duplicated case-insensitively.
  const categoryOptions = (() => {
    const seen = new Set<string>()
    const out: string[] = []
    for (const c of [...CURATED_CATEGORIES, ...(existingCategories || [])]) {
      const key = c.trim().toUpperCase()
      if (c.trim() && !seen.has(key)) {
        seen.add(key)
        out.push(c.trim())
      }
    }
    return out.sort((a, b) => a.localeCompare(b))
  })()

  useEffect(() => {
    if (!bookId) return
    unwrap<{ book: Book; copies: BookCopy[] }>(api.get(`/api/catalog/books/${bookId}`)).then(({ book }) => {
      // If the saved category isn't one of the curated defaults, treat it as "Others"
      const cat = book.category || ''
      setOtherCategory(
        !!cat && !CURATED_CATEGORIES.some((c) => c.toUpperCase() === cat.toUpperCase()),
      )
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
      })
    })
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
          <div className="col-12 mb-3">
            <label className="form-label">
              {t('title')} <span className="text-danger">*</span>
            </label>
            <div className="input-group">
              <input
                className="form-control"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                required
              />
              <button
                type="button"
                className="btn btn-outline-secondary"
                title="Convert title to UPPERCASE"
                onClick={() =>
                  setForm((f) => ({
                    ...f,
                    title: f.title.toUpperCase(),
                    author: f.author.toUpperCase(),
                    publisher: f.publisher.toUpperCase(),
                  }))
                }
              >
                <i className="bi bi-type me-1" />
                UPPERCASE
              </button>
            </div>
            <div className="form-text">Title, author and publisher are saved in capital letters automatically.</div>
          </div>
          {field(t('author'), 'author')}
          {field('ISBN', 'isbn')}
          {field(t('publisher'), 'publisher')}
          {field(t('year'), 'publication_year', { type: 'number', min: 1800, max: 2100 })}
          <div className="col-md-6 mb-3">
            <label className="form-label">{t('category')}</label>
            <select
              className="form-select"
              value={otherCategory ? OTHERS : form.category}
              onChange={(e) => {
                const v = e.target.value
                if (v === OTHERS) {
                  setOtherCategory(true)
                  setForm({ ...form, category: '' })
                } else {
                  setOtherCategory(false)
                  setForm({ ...form, category: v })
                }
              }}
            >
              <option value="">— select —</option>
              {categoryOptions.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
              <option value={OTHERS}>{OTHERS}…</option>
            </select>
            {otherCategory && (
              <input
                className="form-control mt-2"
                placeholder="Enter category"
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              />
            )}
          </div>
          {field('Call Number', 'call_number')}
          <div className="col-md-6 mb-3">
            <label className="form-label">Language</label>
            <select
              className="form-select"
              value={form.language}
              onChange={(e) => setForm({ ...form, language: e.target.value })}
            >
              {/* Preserve an existing value that isn't in our lists. */}
              {form.language &&
                ![...COMMON_LANGUAGES, ...OTHER_LANGUAGES].includes(form.language) && (
                  <option value={form.language}>{form.language}</option>
                )}
              <optgroup label="Common">
                {COMMON_LANGUAGES.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </optgroup>
              <optgroup label="Other languages">
                {OTHER_LANGUAGES.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </optgroup>
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
          <button
            type="button"
            className="btn btn-outline-secondary"
            onClick={() => navigate(bookId ? `/catalog/${bookId}` : '/catalog')}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
