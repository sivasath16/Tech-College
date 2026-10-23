import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export const homeFor = (role) => ({ STUDENT: '/student', RECRUITER: '/recruiter', ADMIN: '/admin' })[role] || '/login'

// Role-based route guard: anonymous -> /login, wrong role -> own dashboard.
export default function ProtectedRoute({ role, children }) {
  const { user, loading } = useAuth()
  if (loading) return <p className="center muted">Loading…</p>
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== role) return <Navigate to={homeFor(user.role)} replace />
  return children
}
