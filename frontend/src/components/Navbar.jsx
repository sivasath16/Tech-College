import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { homeFor } from './ProtectedRoute'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  return (
    <header className="nav">
      <Link to="/" className="brand">🎓 Placement Portal</Link>
      <nav>
        {user ? (
          <>
            <Link to={homeFor(user.role)}>Dashboard</Link>
            <button className="btn ghost" onClick={() => { logout(); navigate('/') }}>Logout</button>
          </>
        ) : (
          <>
            <Link to="/login">Login</Link>
            <Link to="/register/student" className="btn small">Register</Link>
          </>
        )}
      </nav>
    </header>
  )
}
