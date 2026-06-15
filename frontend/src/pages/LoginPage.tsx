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
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

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
              <label className="form-label">{t('username')}</label>
              <input
                className="form-control"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
                required
              />
            </div>
            <div className="mb-4">
              <label className="form-label">{t('password')}</label>
              <input
                type="password"
                className="form-control"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <button className="btn btn-primary w-100" disabled={busy}>
              {busy ? t('loading') : t('login')}
            </button>
          </form>
      </div>
    </div>
  )
}
