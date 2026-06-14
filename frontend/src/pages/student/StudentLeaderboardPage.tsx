import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api, unwrap } from '../../api/client'

// ---- Shapes returned by GET /api/student/leaderboard ----
interface StudentRank {
  rank?: number
  member_id?: string
  full_name?: string
  form_level?: number
  class_group?: string
  borrow_count?: number
}
interface ClassRank {
  form_level?: number
  class_group?: string
  borrow_count?: number
}
interface FormStat {
  form_level?: number
  student_count?: number
  total_borrowed?: number
  avg_borrowed?: number
}
interface LeaderboardData {
  forms: number[]
  selected_form: number | null
  classes_in_form: string[]
  selected_class: string | null
  students: StudentRank[]
  top_students: StudentRank[]
  top_classes: ClassRank[]
  form_stats: FormStat[]
}

/** Gold / silver / bronze badge for the top three ranks, plain number otherwise. */
function RankBadge({ rank }: { rank: number }) {
  const medal = ['#d4af37', '#c0c0c0', '#cd7f32'][rank - 1]
  if (!medal) return <strong>{rank}</strong>
  return (
    <span className="badge" style={{ background: medal, color: rank === 3 ? '#fff' : '#000' }}>
      <i className="bi bi-award-fill" />
    </span>
  )
}

/**
 * NILAM borrowing leaderboard (mirrors the Flask student/leaderboard.html):
 * a main student ranking plus side panels for the top students, the top
 * classes, and per-form statistics. Form/class filters narrow the ranking.
 */
export default function StudentLeaderboardPage() {
  const [form, setForm] = useState<number | ''>('')
  const [klass, setKlass] = useState('') // "class" is a reserved word, so "klass"

  const { data } = useQuery({
    queryKey: ['leaderboard', form, klass],
    queryFn: () =>
      unwrap<LeaderboardData>(
        api.get('/api/student/leaderboard', {
          params: { ...(form ? { form } : {}), ...(klass ? { class: klass } : {}) },
        }),
      ),
  })

  const forms = data?.forms ?? []
  const classesInForm = data?.classes_in_form ?? []
  const students = data?.students ?? []
  const topStudents = data?.top_students ?? []
  const topClasses = data?.top_classes ?? []
  const formStats = data?.form_stats ?? []

  return (
    <div>
      <h4 className="mb-3">
        <i className="bi bi-trophy me-2" />
        NILAM Leaderboard
      </h4>

      {/* ---- Filters: by form, and (when a form is picked) by class ---- */}
      <div className="card shadow-sm mb-4">
        <div className="card-body d-flex flex-wrap align-items-end gap-3">
          <div>
            <label className="form-label fw-semibold mb-1">Filter by Form</label>
            <select
              className="form-select"
              value={form}
              onChange={(e) => {
                setForm(e.target.value ? Number(e.target.value) : '')
                setKlass('') // reset class whenever the form changes
              }}
            >
              <option value="">All forms</option>
              {forms.map((f) => (
                <option key={f} value={f}>
                  Form {f}
                </option>
              ))}
            </select>
          </div>

          {form !== '' && classesInForm.length > 0 && (
            <div>
              <label className="form-label fw-semibold mb-1">Filter by Class</label>
              <select className="form-select" value={klass} onChange={(e) => setKlass(e.target.value)}>
                <option value="">All classes</option>
                {classesInForm.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          )}

          {(form !== '' || klass) && (
            <button
              className="btn btn-outline-secondary"
              onClick={() => {
                setForm('')
                setKlass('')
              }}
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      <div className="row g-4">
        {/* ---- Main ranking: students ordered by books borrowed ---- */}
        <div className="col-lg-8">
          <div className="card shadow-sm h-100">
            <div className="card-header bg-primary text-white">
              <h5 className="mb-0">
                <i className="bi bi-trophy me-2" />
                {form !== '' ? `Form ${form}${klass ? ` - ${klass}` : ''}` : 'Best Borrowers'}
              </h5>
            </div>
            <div className="table-responsive">
              <table className="table table-hover mb-0 align-middle">
                <thead className="table-light">
                  <tr>
                    <th style={{ width: 50 }} className="text-center">
                      #
                    </th>
                    <th>Name</th>
                    <th>Class</th>
                    <th className="text-end">Books Borrowed</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((s, i) => (
                    <tr key={s.member_id || i}>
                      <td className="text-center">
                        <RankBadge rank={s.rank ?? i + 1} />
                      </td>
                      <td className="fw-semibold">{s.full_name}</td>
                      <td>
                        {s.class_group && <span className="badge bg-light text-dark">{s.class_group}</span>}
                      </td>
                      <td className="text-end fw-bold text-primary fs-5">{s.borrow_count ?? 0}</td>
                    </tr>
                  ))}
                  {students.length === 0 && (
                    <tr>
                      <td colSpan={4} className="text-center text-muted py-5">
                        No borrowing data yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* ---- Side panels: top students, top classes, per-form stats ---- */}
        <div className="col-lg-4 d-flex flex-column gap-3">
          {/* Top 3 students */}
          <div className="card shadow-sm">
            <div className="card-header bg-warning-subtle">
              <h6 className="mb-0">
                <i className="bi bi-trophy me-2" />
                Top Students
              </h6>
            </div>
            <ul className="list-group list-group-flush">
              {topStudents.map((s, i) => (
                <li key={s.member_id || i} className="list-group-item d-flex justify-content-between align-items-center">
                  <span>
                    <RankBadge rank={i + 1} /> <span className="ms-1">{s.full_name}</span>
                  </span>
                  <span className="fw-bold text-primary">{s.borrow_count ?? 0}</span>
                </li>
              ))}
              {topStudents.length === 0 && <li className="list-group-item text-muted text-center">No data</li>}
            </ul>
          </div>

          {/* Top 3 classes */}
          <div className="card shadow-sm">
            <div className="card-header bg-info-subtle">
              <h6 className="mb-0">
                <i className="bi bi-people-fill me-2" />
                Top Classes
              </h6>
            </div>
            <ul className="list-group list-group-flush">
              {topClasses.map((c, i) => (
                <li
                  key={`${c.form_level}-${c.class_group}-${i}`}
                  className="list-group-item d-flex justify-content-between align-items-center"
                >
                  <span>
                    <RankBadge rank={i + 1} />{' '}
                    <span className="ms-1">
                      Form {c.form_level} {c.class_group}
                    </span>
                  </span>
                  <span className="fw-bold text-primary">{c.borrow_count ?? 0}</span>
                </li>
              ))}
              {topClasses.length === 0 && <li className="list-group-item text-muted text-center">No data</li>}
            </ul>
          </div>

          {/* Statistics by form */}
          <div className="card shadow-sm">
            <div className="card-header bg-success text-white">
              <h6 className="mb-0">
                <i className="bi bi-bar-chart me-2" />
                Statistics by Form
              </h6>
            </div>
            <ul className="list-group list-group-flush">
              {formStats.map((f) => (
                <li key={f.form_level} className="list-group-item">
                  <div className="d-flex justify-content-between mb-1">
                    <strong>Form {f.form_level}</strong>
                    <span className="badge bg-primary">{f.student_count ?? 0} students</span>
                  </div>
                  <div className="d-flex justify-content-between small text-muted">
                    <span>Total: {f.total_borrowed ?? 0}</span>
                    <span>Average: {(f.avg_borrowed ?? 0).toFixed(1)}</span>
                  </div>
                </li>
              ))}
              {formStats.length === 0 && <li className="list-group-item text-muted text-center">No statistics</li>}
            </ul>
          </div>
        </div>
      </div>

      <div className="mt-4">
        <Link to="/student" className="btn btn-outline-secondary btn-sm">
          <i className="bi bi-arrow-left me-1" />
          Back to home
        </Link>
      </div>
    </div>
  )
}
