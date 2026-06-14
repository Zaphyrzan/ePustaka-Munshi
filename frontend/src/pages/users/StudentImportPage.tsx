import { useState, type ChangeEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from '../../api/client'

interface PreviewStudent {
  full_name: string
  form_level: number | null
  class_group: string | null
  email: string | null
  phone: string | null
}

interface PreviewSheet {
  sheet: string
  format: 'roster' | 'columns'
  form_level: number | null
  class_group: string | null
  students: PreviewStudent[]
}

interface PreviewResponse {
  sheets: PreviewSheet[]
  total: number
  class_groups: string[]
}

interface SheetState extends PreviewSheet {
  include: boolean
  expanded: boolean
}

const FORMS = [1, 2, 3, 4, 5]
const ADD_NEW = '__add_new__'

/** Upload → preview → commit wizard for bulk student import from Excel. */
export default function StudentImportPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [sheets, setSheets] = useState<SheetState[] | null>(null)
  const [classOptions, setClassOptions] = useState<string[]>([])
  const [error, setError] = useState('')
  const [done, setDone] = useState<{ imported: number; errors: string[] } | null>(null)

  const { data: classGroups } = useQuery({
    queryKey: ['class-groups'],
    queryFn: () => unwrap<string[]>(api.get('/api/users/class-groups')),
  })

  const preview = useMutation({
    mutationFn: async (f: File) => {
      const fd = new FormData()
      fd.append('file', f)
      return unwrap<PreviewResponse>(
        api.post('/api/users/members/import/preview', fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
        }),
      )
    },
    onSuccess: (data) => {
      setError('')
      setClassOptions(Array.from(new Set([...(data.class_groups || []), ...(classGroups || [])])))
      setSheets(
        data.sheets.map((s) => ({
          ...s,
          form_level: s.form_level ?? 1,
          include: true,
          expanded: false,
        })),
      )
    },
    onError: (e) => setError(e instanceof Error ? e.message : 'Failed to read file'),
  })

  const commit = useMutation({
    mutationFn: async (students: PreviewStudent[]) =>
      unwrap<{ imported: number; errors: string[] }>(
        api.post('/api/users/members/import/commit', { students }),
      ),
    onSuccess: (res) => {
      setDone(res)
      queryClient.invalidateQueries({ queryKey: ['members'] })
      queryClient.invalidateQueries({ queryKey: ['class-groups'] })
    },
    onError: (e) => setError(e instanceof Error ? e.message : 'Import failed'),
  })

  function onPick(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] || null
    setFile(f)
    setSheets(null)
    setDone(null)
    setError('')
    if (f) preview.mutate(f)
  }

  function patchSheet(idx: number, patch: Partial<SheetState>) {
    setSheets((prev) => (prev ? prev.map((s, i) => (i === idx ? { ...s, ...patch } : s)) : prev))
  }

  function setSheetClass(idx: number, value: string) {
    if (value === ADD_NEW) {
      const name = window.prompt('New class name (e.g. Bestari):')?.trim()
      if (!name) return
      setClassOptions((prev) => Array.from(new Set([...prev, name])).sort())
      // Persist the new class so it survives and shows up elsewhere
      api.post('/api/users/class-groups', { name }).catch(() => {})
      patchSheet(idx, { class_group: name })
    } else {
      patchSheet(idx, { class_group: value || null })
    }
  }

  function doImport() {
    if (!sheets) return
    const students: PreviewStudent[] = []
    for (const s of sheets) {
      if (!s.include) continue
      for (const st of s.students) {
        students.push({
          full_name: st.full_name,
          // Sheet-level form/class override every student in that sheet
          form_level: s.form_level,
          class_group: s.class_group,
          email: st.email,
          phone: st.phone,
        })
      }
    }
    if (students.length === 0) {
      setError('No students selected to import')
      return
    }
    commit.mutate(students)
  }

  const selectedCount = sheets
    ? sheets.filter((s) => s.include).reduce((n, s) => n + s.students.length, 0)
    : 0

  if (done) {
    return (
      <div className="mx-auto" style={{ maxWidth: 720 }}>
        <h4 className="mb-3">Import complete</h4>
        <div className="alert alert-success">
          <i className="bi bi-check-circle me-2" />
          Successfully imported <strong>{done.imported}</strong> student(s).
          <div className="small text-muted mt-1">Default password for each: <code>Munshi123</code></div>
        </div>
        {done.errors.length > 0 && (
          <div className="alert alert-warning">
            <strong>{done.errors.length} row(s) were skipped:</strong>
            <ul className="mb-0 mt-1 small">
              {done.errors.slice(0, 15).map((e, i) => (
                <li key={i}>{e}</li>
              ))}
              {done.errors.length > 15 && <li>… and {done.errors.length - 15} more</li>}
            </ul>
          </div>
        )}
        <div className="d-flex gap-2">
          <button className="btn btn-primary" onClick={() => navigate('/users')}>
            Back to members
          </button>
          <button
            className="btn btn-outline-secondary"
            onClick={() => {
              setFile(null)
              setSheets(null)
              setDone(null)
            }}
          >
            Import another file
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto" style={{ maxWidth: 860 }}>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h4 className="mb-0">Import students from Excel</h4>
        <button className="btn btn-outline-secondary btn-sm" onClick={() => navigate('/users')}>
          Cancel
        </button>
      </div>

      <div className="card shadow-sm p-4 mb-3">
        <label className="form-label fw-semibold">Excel file (.xlsx, .xls, .csv)</label>
        <input
          type="file"
          className="form-control"
          accept=".xlsx,.xls,.csv"
          onChange={onPick}
        />
        <div className="form-text">
          Works with the school name lists (one sheet per class, e.g. “1 BESTARI”) and with
          structured files that have column headers. Each sheet’s class and form can be adjusted
          below before importing.
        </div>
        {file && preview.isPending && <div className="text-muted mt-2">Reading {file.name}…</div>}
      </div>

      {error && <div className="alert alert-danger py-2">{error}</div>}

      {sheets && (
        <>
          <div className="d-flex justify-content-between align-items-center mb-2">
            <span className="text-muted">
              {sheets.length} sheet(s) · {selectedCount} student(s) selected
            </span>
            <button className="btn btn-success" disabled={commit.isPending || selectedCount === 0} onClick={doImport}>
              {commit.isPending ? 'Importing…' : `Import ${selectedCount} student(s)`}
            </button>
          </div>

          {sheets.map((s, idx) => (
            <div className="card shadow-sm mb-2" key={s.sheet}>
              <div className="card-body">
                <div className="d-flex align-items-center gap-3 flex-wrap">
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      checked={s.include}
                      id={`inc-${idx}`}
                      onChange={(e) => patchSheet(idx, { include: e.target.checked })}
                    />
                    <label className="form-check-label fw-semibold" htmlFor={`inc-${idx}`}>
                      {s.sheet}
                    </label>
                  </div>
                  <span className="badge bg-info text-dark">{s.students.length} students</span>

                  <div className="d-flex align-items-center gap-1 ms-auto">
                    <label className="form-label mb-0 small text-muted">Form</label>
                    <select
                      className="form-select form-select-sm"
                      style={{ width: 100 }}
                      value={s.form_level ?? 1}
                      onChange={(e) => patchSheet(idx, { form_level: Number(e.target.value) })}
                    >
                      {FORMS.map((n) => (
                        <option key={n} value={n}>
                          Form {n}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="d-flex align-items-center gap-1">
                    <label className="form-label mb-0 small text-muted">Class</label>
                    <select
                      className="form-select form-select-sm"
                      style={{ width: 180 }}
                      value={s.class_group || ''}
                      onChange={(e) => setSheetClass(idx, e.target.value)}
                    >
                      <option value="">— none —</option>
                      {classOptions.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                      {s.class_group && !classOptions.includes(s.class_group) && (
                        <option value={s.class_group}>{s.class_group}</option>
                      )}
                      <option value={ADD_NEW}>+ Add new class…</option>
                    </select>
                  </div>

                  <button
                    className="btn btn-link btn-sm text-decoration-none"
                    onClick={() => patchSheet(idx, { expanded: !s.expanded })}
                  >
                    {s.expanded ? 'Hide names' : 'Show names'}
                  </button>
                </div>

                {s.expanded && (
                  <ol className="small text-muted mt-2 mb-0" style={{ columns: 2 }}>
                    {s.students.map((st, i) => (
                      <li key={i}>{st.full_name}</li>
                    ))}
                  </ol>
                )}
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
