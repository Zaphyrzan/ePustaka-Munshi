import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
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

// Gold / silver / bronze for ranks 1-3.
const MEDAL = ['#d4af37', '#c0c0c0', '#cd7f32']

/** Round medal badge with an award icon (used in the main ranking table). */
function Medal({ rank }: { rank: number }) {
  const color = MEDAL[rank - 1]
  if (!color) return <strong>{rank}</strong>
  return (
    <span
      className="d-inline-flex align-items-center justify-content-center"
      style={{ width: 30, height: 30, borderRadius: '50%', background: color, color: rank === 3 ? '#fff' : '#1f2a37' }}
    >
      <i className="bi bi-award-fill" />
    </span>
  )
}

interface PodiumEntry {
  name: string
  sub?: string
  value: number
}

/**
 * Winner podium for a top-three ranking. First place sits in the middle on the
 * tallest pedestal, flanked by second (left) and third (right). The rank shows
 * on the pedestal block, and a coloured ring frames each avatar.
 */
function Top3Podium({ title, icon, entries }: { title: string; icon: string; entries: PodiumEntry[] }) {
  const { t } = useTranslation()
  // Render order is 2nd, 1st, 3rd; pedestal height encodes the rank.
  const slots = [
    { e: entries[1], rank: 2, height: 52 },
    { e: entries[0], rank: 1, height: 74 },
    { e: entries[2], rank: 3, height: 38 },
  ]

  return (
    <div className="card shadow-sm h-100">
      <div className="card-header bg-transparent fw-semibold">
        <i className={`bi ${icon} me-2`} />
        {title}
      </div>
      <div className="card-body pb-0">
        {entries.length === 0 ? (
          <div className="text-muted text-center py-3">{t('noData')}</div>
        ) : (
          <div className="d-flex justify-content-center align-items-end gap-2 text-center">
            {slots.map(({ e, rank, height }) => {
              if (!e) return <div key={rank} style={{ flex: 1 }} />
              const color = MEDAL[rank - 1]
              const isFirst = rank === 1
              const avatar = isFirst ? 52 : 42
              return (
                <div key={rank} style={{ flex: 1, minWidth: 0 }}>
                  {isFirst && <i className="bi bi-trophy-fill d-block mb-1" style={{ color, fontSize: 18 }} />}
                  <div
                    className="mx-auto d-flex align-items-center justify-content-center"
                    style={{
                      width: avatar,
                      height: avatar,
                      borderRadius: '50%',
                      background: '#f1f3f5',
                      border: `3px solid ${color}`,
                      color: '#495057',
                      fontSize: isFirst ? 24 : 18,
                    }}
                  >
                    <i className="bi bi-person-fill" />
                  </div>
                  <div className="fw-semibold small text-truncate mt-1">{e.name}</div>
                  {e.sub && (
                    <div className="text-muted text-truncate" style={{ fontSize: '0.72rem' }}>
                      {e.sub}
                    </div>
                  )}
                  <div className="fw-bold text-primary">{e.value}</div>
                  {/* Pedestal block - taller = higher rank */}
                  <div
                    className="rounded-top mt-1 mx-auto d-flex align-items-center justify-content-center fw-bold"
                    style={{ height, width: '80%', background: color, color: rank === 3 ? '#fff' : '#1f2a37' }}
                  >
                    {rank}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Leaderboard (mirrors the Flask student/leaderboard.html):
 * top-3 podiums for students, classes and forms, plus the full student
 * ranking. Form/class filters narrow the ranking.
 *
 * NOTE: this ranks by number of books *borrowed* - it is NOT the school's
 * separate NILAM (reading) programme.
 */
export default function StudentLeaderboardPage() {
  const { t } = useTranslation()
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

  // Top 3 forms by total books borrowed (the API returns all forms unsorted).
  const topForms = [...formStats]
    .sort((a, b) => (b.total_borrowed ?? 0) - (a.total_borrowed ?? 0))
    .slice(0, 3)

  // Map each ranking into the podium's { name, sub, value } shape.
  const studentPodium: PodiumEntry[] = topStudents.map((s) => ({
    name: s.full_name ?? '-',
    sub: s.class_group,
    value: s.borrow_count ?? 0,
  }))
  const classPodium: PodiumEntry[] = topClasses.map((c) => ({
    name: `${t('form')} ${c.form_level} ${c.class_group ?? ''}`.trim(),
    value: c.borrow_count ?? 0,
  }))
  const formPodium: PodiumEntry[] = topForms.map((f) => ({
    name: `${t('form')} ${f.form_level}`,
    sub: t('studentsCount', { count: f.student_count ?? 0 }),
    value: f.total_borrowed ?? 0,
  }))

  return (
    <div>
      <h4 className="mb-3">
        <i className="bi bi-trophy me-2" />
        {t('leaderboard')}
      </h4>

      {/* ---- Top-3 podiums: students, classes, forms ---- */}
      <div className="row g-3 mb-4">
        <div className="col-lg-4">
          <Top3Podium title={t('top3Students')} icon="bi-person-fill" entries={studentPodium} />
        </div>
        <div className="col-lg-4">
          <Top3Podium title={t('top3Classes')} icon="bi-people-fill" entries={classPodium} />
        </div>
        <div className="col-lg-4">
          <Top3Podium title={t('top3Forms')} icon="bi-bar-chart" entries={formPodium} />
        </div>
      </div>

      {/* ---- Filters: by form, and (when a form is picked) by class ---- */}
      <div className="card shadow-sm mb-4">
        <div className="card-body d-flex flex-wrap align-items-end gap-3">
          <div>
            <label className="form-label fw-semibold mb-1">{t('filterByForm')}</label>
            <select
              className="form-select"
              value={form}
              onChange={(e) => {
                setForm(e.target.value ? Number(e.target.value) : '')
                setKlass('') // reset class whenever the form changes
              }}
            >
              <option value="">{t('allForms')}</option>
              {forms.map((f) => (
                <option key={f} value={f}>
                  {t('form')} {f}
                </option>
              ))}
            </select>
          </div>

          {form !== '' && classesInForm.length > 0 && (
            <div>
              <label className="form-label fw-semibold mb-1">{t('filterByClass')}</label>
              <select className="form-select" value={klass} onChange={(e) => setKlass(e.target.value)}>
                <option value="">{t('allClasses')}</option>
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
              {t('clearFilters')}
            </button>
          )}
        </div>
      </div>

      {/* ---- Full student ranking ---- */}
      <div className="card shadow-sm">
        <div className="card-header bg-primary text-white">
          <h5 className="mb-0">
            <i className="bi bi-trophy me-2" />
            {form !== '' ? `${t('form')} ${form}${klass ? ` - ${klass}` : ''}` : t('bestBorrowers')}
          </h5>
        </div>
        <div className="table-responsive">
          <table className="table table-hover mb-0 align-middle">
            <thead className="table-light">
              <tr>
                <th style={{ width: 60 }} className="text-center">
                  #
                </th>
                <th>{t('name')}</th>
                <th>{t('studentClass')}</th>
                <th className="text-end">{t('booksBorrowed')}</th>
              </tr>
            </thead>
            <tbody>
              {students.map((s, i) => (
                <tr key={s.member_id || i}>
                  <td className="text-center">
                    <Medal rank={s.rank ?? i + 1} />
                  </td>
                  <td className="fw-semibold">{s.full_name}</td>
                  <td>{s.class_group && <span className="badge bg-light text-dark">{s.class_group}</span>}</td>
                  <td className="text-end fw-bold text-primary fs-5">{s.borrow_count ?? 0}</td>
                </tr>
              ))}
              {students.length === 0 && (
                <tr>
                  <td colSpan={4} className="text-center text-muted py-5">
                    {t('noBorrowingData')}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-4">
        <Link to="/student" className="btn btn-outline-secondary btn-sm">
          <i className="bi bi-arrow-left me-1" />
          {t('backToHome')}
        </Link>
      </div>
    </div>
  )
}
