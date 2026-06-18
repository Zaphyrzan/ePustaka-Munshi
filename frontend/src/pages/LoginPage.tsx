import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/AuthContext'

// Served straight from the CDN (frontend/public), so it never waits on the
// Flask serverless function to cold-start.
const LOGO = '/images/school-logo.jpg'

export default function LoginPage() {
  const { login } = useAuth()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [showHelp, setShowHelp] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const session = await login(username, password)
      navigate(session.user_type === 'student' ? '/student' : '/dashboard')
    } catch {
      setError(t('invalidLogin'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="text-center mb-4">
          <img src={LOGO} alt="SMK Abdullah Munshi" className="login-logo mb-3" />
          <h4 className="mb-1 fw-bold" style={{ color: 'var(--primary-color)' }}>
            {t('appName')}
          </h4>
          <p className="text-muted small mb-0">SMK Abdullah Munshi</p>
          <p className="text-muted mb-0" style={{ fontSize: '0.75rem' }}>
            Library Management System
          </p>
        </div>
        {error && <div className="alert alert-danger py-2">{error}</div>}
        <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label className="form-label">{t('memberIdLogin')}</label>
              <div className="input-group">
                <span className="input-group-text">
                  <i className="bi bi-person-vcard" />
                </span>
                <input
                  className="form-control"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. STU0001"
                  autoFocus
                  required
                />
              </div>
            </div>
            <div className="mb-4">
              <label className="form-label">{t('password')}</label>
              <div className="input-group">
                <span className="input-group-text">
                  <i className="bi bi-lock" />
                </span>
                <input
                  type={showPw ? 'text' : 'password'}
                  className="form-control"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  onClick={() => setShowPw((v) => !v)}
                  tabIndex={-1}
                  aria-label={showPw ? t('hidePassword') : t('showPassword')}
                  title={showPw ? t('hidePassword') : t('showPassword')}
                >
                  <i className={`bi ${showPw ? 'bi-eye-slash' : 'bi-eye'}`} />
                </button>
              </div>
            </div>
            <button className="btn btn-primary w-100" disabled={busy}>
              {busy ? t('loading') : t('login')}
            </button>
          </form>

          <div className="text-center mt-3">
            <button
              type="button"
              className="btn btn-link btn-sm text-muted text-decoration-none p-0"
              onClick={() => setShowHelp((v) => !v)}
            >
              {t('forgotPassword')}
            </button>
          </div>
          {showHelp && (
            <div className="alert alert-info small mt-2 mb-0">
              <i className="bi bi-info-circle me-1" />
              {t('forgotPasswordHelp')}
            </div>
          )}
      </div>
    </div>
  )
}
