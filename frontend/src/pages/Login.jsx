import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { errorMessage } from '../api'
import Field from '../components/Field'
import { homeFor } from '../components/ProtectedRoute'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const { state } = useLocation()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      navigate(homeFor(await login(form.email, form.password)))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="card form narrow" onSubmit={submit}>
      <h2>Sign in</h2>
      <p className="muted">Students, recruiters and placement cell staff sign in here.</p>
      {state?.registered && <div className="alert ok">Registration successful. Please sign in.</div>}
      {error && <div className="alert error">{error}</div>}
      <Field label="Email"><input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
      <Field label="Password"><input type="password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
      <button className="btn" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
      <p className="muted">New here? <Link to="/register/student">Register as student</Link> or <Link to="/register/recruiter">recruiter</Link>.</p>
    </form>
  )
}
