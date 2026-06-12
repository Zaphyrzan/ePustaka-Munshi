import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/AuthContext'

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
    <div className="d-flex align-items-center justify-content-center min-vh-100 bg-light">
      <div className="card shadow-sm" style={{ width: 380 }}>
        <div className="card-body p-4">
          <h4 className="text-center mb-1 fw-bold">
            <i className="bi bi-book me-2 text-primary" />
            {t('appName')}
          </h4>
          <p className="text-center text-muted small mb-4">SMK Abdullah Munshi</p>
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
    </div>
  )
}
