import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/AuthContext'
import { setLanguage } from '../i18n'
import { api, unwrap } from '../api/client'
import type { CirculationStats } from '../types'

const STAFF_ROLES = ['Administrator', 'Librarian', 'Library Prefect']
// Served straight from the CDN (frontend/public), not the Flask function.
const LOGO = '/images/school-logo.jpg'

interface NavItem {
  to: string
  icon: string
  label: string
  end?: boolean
  badge?: number
}
interface NavSection {
  title: string
  items: NavItem[]
}

export default function Layout() {
  const { session, logout } = useAuth()
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const isStaff = session?.user_type === 'staff' && STAFF_ROLES.includes(session.role)

  // Close the profile dropdown on outside click
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  async function handleLogout() {
    setMenuOpen(false)
    await logout()
    navigate('/login')
  }

  // Library Prefects get catalog + circulation only; OCR and member/staff
  // administration are for Librarians and Administrators.
  const isAdminOrLibrarian = session?.role === 'Administrator' || session?.role === 'Librarian'
  // A Library Prefect is a promoted student, so they keep their student portal
  // (home, search, my loans, NILAM leaderboard) alongside their prefect tools.
  const isPrefect = session?.role === 'Library Prefect'

  const { data: statsData } = useQuery({
    queryKey: ['circulation-stats'],
    queryFn: () => unwrap<CirculationStats>(api.get('/api/circulation/stats')),
    enabled: isStaff,
    staleTime: 60_000,
  })
  const staffOverdue = statsData?.overdue_loans ?? 0

  interface StudentLoansData { active?: { items?: { status: string; is_overdue?: boolean }[] } }
  const { data: studentLoansData } = useQuery({
    queryKey: ['student-loans-full'],
    queryFn: () => unwrap<StudentLoansData>(api.get('/api/student/loans')),
    enabled: !isStaff || isPrefect,
    staleTime: 60_000,
  })
  const studentOverdue = (studentLoansData?.active?.items ?? []).filter(
    (l) => l.status === 'overdue' || l.is_overdue,
  ).length

  const studentPortalSection: NavSection = {
    title: t('student_portal'),
    items: [
      { to: '/student', icon: 'bi-house', label: t('home'), end: true },
      { to: '/student/search', icon: 'bi-search', label: t('search') },
      {
        to: '/student/loans',
        icon: 'bi-journal-bookmark',
        label: t('myLoans'),
        badge: studentOverdue || undefined,
      },
      { to: '/student/leaderboard', icon: 'bi-trophy', label: t('leaderboard') },
    ],
  }

  const sections: NavSection[] = isStaff
    ? [
        { title: t('staff_functions'), items: [{ to: '/dashboard', icon: 'bi-speedometer2', label: t('dashboard') }] },
        { title: t('catalog'), items: [{ to: '/catalog', icon: 'bi-book', label: t('books') }] },
        {
          title: t('circulation'),
          items: [
            { to: '/circulation/checkout', icon: 'bi-box-arrow-right', label: t('checkout') },
            { to: '/circulation/return', icon: 'bi-box-arrow-in-left', label: t('return') },
            {
              to: '/circulation',
              icon: 'bi-list-check',
              label: t('activeLoans'),
              end: true,
              badge: staffOverdue || undefined,
            },
          ],
        },
        ...(isAdminOrLibrarian
          ? [
              { title: t('digitization'), items: [{ to: '/ocr', icon: 'bi-file-earmark-text', label: t('ocr') }] },
              { title: t('administration'), items: [{ to: '/users', icon: 'bi-people', label: t('users') }] },
            ]
          : []),
        ...(isPrefect ? [studentPortalSection] : []),
      ]
    : [studentPortalSection]

  return (
    <div>
      <nav className={`app-sidebar${open ? ' open' : ''}`}>
        <div className="sidebar-brand d-flex align-items-center">
          <img
            src={LOGO}
            alt="SMK Abdullah Munshi"
            className="me-2 rounded"
            style={{ width: 40, height: 40, objectFit: 'contain', background: '#fff', padding: 2 }}
          />
          <div>
            <div style={{ fontSize: '0.95rem', lineHeight: 1.2, fontWeight: 600 }}>ePustaka</div>
            <div style={{ fontSize: '0.7rem', opacity: 0.8 }}>SMK Abdullah Munshi</div>
          </div>
        </div>

        <ul className="nav flex-column">
          {sections.map((section) => (
            <li key={section.title}>
              <ul className="nav flex-column">
                <li className="sidebar-section">{section.title}</li>
                {section.items.map((item) => (
                  <li className="nav-item" key={item.to}>
                    <NavLink className="nav-link d-flex align-items-center justify-content-between" to={item.to} end={item.end} onClick={() => setOpen(false)}>
                      <span>
                        <i className={`bi ${item.icon} me-1`} />
                        {item.label}
                      </span>
                      {item.badge ? (
                        <span className="badge bg-danger rounded-pill">{item.badge}</span>
                      ) : null}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </nav>

      <div className="app-main">
        <div className="app-topbar">
          <button className="btn btn-outline-secondary btn-sm d-lg-none" onClick={() => setOpen((v) => !v)}>
            <i className="bi bi-list" />
          </button>
          <div className="flex-grow-1" />
          <div className="d-flex align-items-center gap-3">
            <div className="d-flex align-items-center">
              <i className="bi bi-globe2 me-1 text-muted" />
              <select
                className="form-select form-select-sm"
                style={{ width: 'auto' }}
                value={i18n.language.startsWith('ms') ? 'ms' : 'en'}
                onChange={(e) => setLanguage(e.target.value as 'en' | 'ms')}
                aria-label="Language"
              >
                <option value="en">English</option>
                <option value="ms">Bahasa Melayu</option>
              </select>
            </div>

            {/* Profile dropdown (React-controlled; app doesn't bundle Bootstrap JS) */}
            <div className="position-relative" ref={menuRef}>
              <button
                className="btn btn-light btn-sm d-flex align-items-center gap-2"
                onClick={() => setMenuOpen((v) => !v)}
              >
                <i className="bi bi-person-circle fs-5" />
                <span className="d-none d-sm-inline text-truncate" style={{ maxWidth: 160 }}>
                  {session?.user.full_name || session?.user.username || session?.user.member_id}
                </span>
                <i className="bi bi-chevron-down small" />
              </button>
              {menuOpen && (
                <ul
                  className="dropdown-menu show shadow"
                  style={{ position: 'absolute', right: 0, top: '100%', display: 'block', minWidth: 200 }}
                >
                  <li className="px-3 py-2 border-bottom">
                    <div className="fw-semibold text-truncate">{session?.user.full_name}</div>
                    <div className="small text-muted">{session?.role}</div>
                  </li>
                  <li>
                    <Link className="dropdown-item" to="/profile" onClick={() => setMenuOpen(false)}>
                      <i className="bi bi-person me-2" />
                      {t('profile')}
                    </Link>
                  </li>
                  <li>
                    <Link className="dropdown-item" to="/change-password" onClick={() => setMenuOpen(false)}>
                      <i className="bi bi-key me-2" />
                      {t('changePassword') || 'Change Password'}
                    </Link>
                  </li>
                  <li>
                    <hr className="dropdown-divider" />
                  </li>
                  <li>
                    <button className="dropdown-item text-danger" onClick={handleLogout}>
                      <i className="bi bi-box-arrow-right me-2" />
                      {t('logout')}
                    </button>
                  </li>
                </ul>
              )}
            </div>
          </div>
        </div>

        <main className="app-content">
          <Outlet />
        </main>
      </div>

      {open && (
        <div
          className="d-lg-none position-fixed top-0 start-0 w-100 h-100"
          style={{ background: 'rgba(0,0,0,0.4)', zIndex: 1035 }}
          onClick={() => setOpen(false)}
        />
      )}
    </div>
  )
}
