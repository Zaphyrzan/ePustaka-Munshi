import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, unwrap } from '../../api/client'
import type { Book, BookCopy } from '../../types'
import Barcode from '../../components/Barcode'

export default function PrintBarcodesPage() {
  const { bookId } = useParams()
  const { t } = useTranslation()
  const [selected, setSelected] = useState<Set<number>>(new Set())

  const { data, isLoading } = useQuery({
    queryKey: ['book', bookId],
    queryFn: () => unwrap<{ book: Book; copies: BookCopy[] }>(api.get(`/api/catalog/books/${bookId}`)),
  })

  // Default to selecting every copy that has a barcode.
  useEffect(() => {
    if (data) setSelected(new Set(data.copies.filter((c) => c.barcode).map((c) => c.id)))
  }, [data])

  if (isLoading) return <div className="text-muted py-5 text-center">{t('loading')}</div>
  if (!data) return <div className="alert alert-warning">{t('bookNotFound')}</div>

  const { book, copies } = data
  const printable = copies.filter((c) => c.barcode)
  const toPrint = printable.filter((c) => selected.has(c.id))

  function toggle(id: number) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div>
      {/* Controls — hidden when printing */}
      <div className="no-print">
        <nav className="mb-3">
          <Link to={`/catalog/${book.id}`} className="text-decoration-none">
            ‹ {book.title}
          </Link>
        </nav>
        <div className="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
          <h4 className="mb-0">Print barcodes</h4>
          <div className="d-flex gap-2">
            <button
              className="btn btn-outline-secondary btn-sm"
              onClick={() => setSelected(new Set(printable.map((c) => c.id)))}
            >
              Select all
            </button>
            <button className="btn btn-outline-secondary btn-sm" onClick={() => setSelected(new Set())}>
              Clear
            </button>
            <button className="btn btn-primary" disabled={toPrint.length === 0} onClick={() => window.print()}>
              <i className="bi bi-printer me-1" />
              Print ({toPrint.length})
            </button>
          </div>
        </div>

        {printable.length === 0 && (
          <div className="alert alert-warning">None of this book's copies have a barcode yet.</div>
        )}

        {/* Selection list */}
        {printable.length > 0 && (
          <div className="card mb-4">
            <table className="table table-hover mb-0 align-middle">
              <thead className="table-light">
                <tr>
                  <th style={{ width: 36 }} />
                  <th>{t('accessionNo')}</th>
                  <th>{t('barcode')}</th>
                </tr>
              </thead>
              <tbody>
                {printable.map((c) => (
                  <tr key={c.id} style={{ cursor: 'pointer' }} onClick={() => toggle(c.id)}>
                    <td>
                      <input
                        type="checkbox"
                        className="form-check-input"
                        checked={selected.has(c.id)}
                        onChange={() => toggle(c.id)}
                      />
                    </td>
                    <td>{c.accession_number}</td>
                    <td className="font-monospace">{c.barcode}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Printable header */}
      {toPrint.length > 0 && (
        <div className="barcode-print-header">
          <h2>{book.title}</h2>
          <p>
            {t('author')}: {book.author || '—'}
          </p>
          <p>
            {t('totalBarcodes')}: {toPrint.length}
          </p>
        </div>
      )}

      {/* Printable label sheet */}
      <div className="barcode-sheet">
        {toPrint.map((c) => (
          <div key={c.id} className="barcode-label">
            <div className="barcode-label-title">{book.title}</div>
            <Barcode value={c.barcode!} height={45} />
            <div className="barcode-label-acc">{c.accession_number}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
