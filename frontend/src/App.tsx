import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import ChangePasswordPage from './pages/ChangePasswordPage'
import CatalogListPage from './pages/catalog/CatalogListPage'
import BookDetailPage from './pages/catalog/BookDetailPage'
import BookFormPage from './pages/catalog/BookFormPage'
import LoansPage from './pages/circulation/LoansPage'
import CheckoutPage from './pages/circulation/CheckoutPage'
import ReturnPage from './pages/circulation/ReturnPage'
import OcrJobsPage from './pages/ocr/OcrJobsPage'
import OcrReviewPage from './pages/ocr/OcrReviewPage'
import UsersPage from './pages/users/UsersPage'
import MemberFormPage from './pages/users/MemberFormPage'
import StudentImportPage from './pages/users/StudentImportPage'
import StaffFormPage from './pages/users/StaffFormPage'
import StudentPortalPage from './pages/student/StudentPortalPage'
import StudentSearchPage from './pages/student/StudentSearchPage'
import StudentLoansPage from './pages/student/StudentLoansPage'
import StudentLeaderboardPage from './pages/student/StudentLeaderboardPage'

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

/** Send each role to its own landing page (students must NOT see the staff dashboard). */
function HomeRedirect() {
  const { session } = useAuth()
  return <Navigate to={session?.user_type === 'student' ? '/student' : '/dashboard'} replace />
}

/** Guard staff-only pages: a student who reaches one is bounced to their portal. */
function StaffOnly({ children }: { children: React.ReactNode }) {
  const { session } = useAuth()
  if (session?.user_type === 'student') return <Navigate to="/student" replace />
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
        <Route path="/" element={<HomeRedirect />} />
        <Route path="/dashboard" element={<StaffOnly><DashboardPage /></StaffOnly>} />
        <Route path="/change-password" element={<ChangePasswordPage />} />
        {/* Catalog browse/detail is open to students; create/edit is staff-only */}
        <Route path="/catalog" element={<CatalogListPage />} />
        <Route path="/catalog/add" element={<StaffOnly><BookFormPage /></StaffOnly>} />
        <Route path="/catalog/:bookId" element={<BookDetailPage />} />
        <Route path="/catalog/:bookId/edit" element={<StaffOnly><BookFormPage /></StaffOnly>} />
        <Route path="/circulation" element={<StaffOnly><LoansPage /></StaffOnly>} />
        <Route path="/circulation/checkout" element={<StaffOnly><CheckoutPage /></StaffOnly>} />
        <Route path="/circulation/return" element={<StaffOnly><ReturnPage /></StaffOnly>} />
        <Route path="/ocr" element={<StaffOnly><OcrJobsPage /></StaffOnly>} />
        <Route path="/ocr/:jobId/review" element={<StaffOnly><OcrReviewPage /></StaffOnly>} />
        <Route path="/users" element={<StaffOnly><UsersPage /></StaffOnly>} />
        <Route path="/users/members/add" element={<StaffOnly><MemberFormPage /></StaffOnly>} />
        <Route path="/users/members/import" element={<StaffOnly><StudentImportPage /></StaffOnly>} />
        <Route path="/users/members/:memberId/edit" element={<StaffOnly><MemberFormPage /></StaffOnly>} />
        <Route path="/users/staff/add" element={<StaffOnly><StaffFormPage /></StaffOnly>} />
        <Route path="/users/staff/:userId/edit" element={<StaffOnly><StaffFormPage /></StaffOnly>} />
        <Route path="/student" element={<StudentPortalPage />} />
        <Route path="/student/search" element={<StudentSearchPage />} />
        <Route path="/student/loans" element={<StudentLoansPage />} />
        <Route path="/student/leaderboard" element={<StudentLeaderboardPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
