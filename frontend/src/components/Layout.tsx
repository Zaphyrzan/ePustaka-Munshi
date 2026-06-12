import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/AuthContext'
import { setLanguage } from '../i18n'

const STAFF_ROLES = ['Administrator', 'Librarian', 'Student Assistant']

export default function Layout() {
  const { session, logout } = useAuth()
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const isStaff = session?.user_type === 'staff' && STAFF_ROLES.includes(session.role)

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div className="d-flex flex-column min-vh-100">
      <nav className="navbar navbar-expand-lg navbar-dark bg-primary px-3">
        <span className="navbar-brand fw-bold">
          <i className="bi bi-book me-2" />
          {t('appName')}
        </span>
        <div className="navbar-nav flex-row gap-3 me-auto">
          <NavLink className="nav-link" to="/dashboard">
            {t('dashboard')}
          </NavLink>
          <NavLink className="nav-link" to="/catalog">
            {t('catalog')}
          </NavLink>
          {isStaff && (
            <>
              <NavLink className="nav-link" to="/circulation">
                {t('circulation')}
              </NavLink>
              <NavLink className="nav-link" to="/ocr">
                {t('ocr')}
              </NavLink>
              <NavLink className="nav-link" to="/users">
                {t('users')}
              </NavLink>
            </>
          )}
        </div>
        <div className="d-flex align-items-center gap-3">
          <div className="btn-group btn-group-sm">
            <button
              className={`btn btn-outline-light ${i18n.language === 'en' ? 'active' : ''}`}
              onClick={() => setLanguage('en')}
            >
              EN
            </button>
            <button
              className={`btn btn-outline-light ${i18n.language === 'ms' ? 'active' : ''}`}
              onClick={() => setLanguage('ms')}
            >
              BM
            </button>
          </div>
          <span className="text-white-50 small">
            {session?.user.full_name || session?.user.username || session?.user.member_id}
          </span>
          <button className="btn btn-outline-light btn-sm" onClick={handleLogout}>
            <i className="bi bi-box-arrow-right me-1" />
            {t('logout')}
          </button>
        </div>
      </nav>
      <main className="container-fluid py-4 px-4 flex-grow-1">
        <Outlet />
      </main>
    </div>
  )
}
