import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/AuthContext'
import { API_BASE } from '../api/client'
import { setLanguage } from '../i18n'

const STAFF_ROLES = ['Administrator', 'Librarian', 'Library Prefect']
const LOGO = `${API_BASE}/static/images/Lencana_Sekolah_Menengah_Kebangsaan_Abdullah_Munshi.jpg`

interface NavItem {
  to: string
  icon: string
  label: string
  end?: boolean
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

  const sections: NavSection[] = isStaff
    ? [
        { title: t('staff_functions'), items: [{ to: '/dashboard', icon: 'bi-speedometer2', label: t('dashboard') }] },
        { title: t('catalog'), items: [{ to: '/catalog', icon: 'bi-book', label: t('books') }] },
        {
          title: t('circulation'),
          items: [
            { to: '/circulation/checkout', icon: 'bi-box-arrow-right', label: t('checkout') },
            { to: '/circulation/return', icon: 'bi-box-arrow-in-left', label: t('return') },
            { to: '/circulation', icon: 'bi-list-check', label: t('activeLoans'), end: true },
          ],
        },
        { title: t('digitization'), items: [{ to: '/ocr', icon: 'bi-file-earmark-text', label: t('ocr') }] },
        { title: t('administration'), items: [{ to: '/users', icon: 'bi-people', label: t('users') }] },
      ]
    : [
        {
          title: t('student_portal'),
          items: [
            { to: '/student', icon: 'bi-house', label: t('home'), end: true },
            { to: '/student/search', icon: 'bi-search', label: t('search') },
            { to: '/student/loans', icon: 'bi-journal-bookmark', label: t('myLoans') },
            { to: '/student/leaderboard', icon: 'bi-trophy', label: t('leaderboard') },
          ],
        },
      ]

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
                    <NavLink className="nav-link" to={item.to} end={item.end} onClick={() => setOpen(false)}>
                      <i className={`bi ${item.icon}`} />
                      {item.label}
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
            <div className="btn-group btn-group-sm">
              <button
                className={`btn btn-outline-secondary ${i18n.language === 'en' ? 'active' : ''}`}
                onClick={() => setLanguage('en')}
              >
                EN
              </button>
              <button
                className={`btn btn-outline-secondary ${i18n.language === 'ms' ? 'active' : ''}`}
                onClick={() => setLanguage('ms')}
              >
                BM
              </button>
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
