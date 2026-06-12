import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import CatalogListPage from './pages/catalog/CatalogListPage'
import BookDetailPage from './pages/catalog/BookDetailPage'

function Protected({ children }: { children: React.ReactNode }) {
  const { session, loading } = useAuth()
  if (loading) {
    return (
      <div className="d-flex align-items-center justify-content-center min-vh-100 text-muted">
        Loading...
      </div>
    )
  }
  if (!session) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/catalog" element={<CatalogListPage />} />
        <Route path="/catalog/:bookId" element={<BookDetailPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
