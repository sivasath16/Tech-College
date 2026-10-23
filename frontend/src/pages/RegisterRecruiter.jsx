import { useState } from 'react'
import { Link } from 'react-router-dom'
import api, { errorMessage } from '../api'
import Field from '../components/Field'

const MAX_LOGO = 2 * 1024 * 1024

export default function RegisterRecruiter() {
  const [form, setForm] = useState({ company_name: '', contact_person: '', email: '', phone: '', company_profile: '', password: '' })
  const [logo, setLogo] = useState(null)
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const pickLogo = (e) => {
    const file = e.target.files[0]
    setError('')
    if (file && !['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) { setError('Logo must be PNG, JPEG or WebP'); return }
    if (file && file.size > MAX_LOGO) { setError('Logo must be 2 MB or smaller'); return }
    setLogo(file)
  }

  const submit = async (e) => {
    e.preventDefault()
    if (!logo) { setError('Please upload your company logo'); return }
    setError(''); setBusy(true)
    const data = new FormData()
    Object.entries(form).forEach(([k, v]) => data.append(k, v))
    data.append('logo', logo)
    try {
      await api.post('/auth/register/recruiter', data)
      setDone(true)
    } catch (err) { setError(errorMessage(err)) } finally { setBusy(false) }
  }

  if (done) {
    return (
      <div className="card narrow center">
        <h2>Registration submitted</h2>
        <p>Your company is now <b>pending verification</b> by the placement cell. You can sign in once it is approved.</p>
        <Link className="btn" to="/">Back to home</Link>
      </div>
    )
  }

  return (
    <form className="card form" onSubmit={submit}>
      <h2>Recruiter registration</h2>
      <p className="muted">Recruiter accounts are activated after Admin verification.</p>
      {error && <div className="alert error">{error}</div>}
      <div className="cols">
        <Field label="Company name"><input required value={form.company_name} onChange={set('company_name')} /></Field>
        <Field label="Contact person"><input required value={form.contact_person} onChange={set('contact_person')} /></Field>
        <Field label="Company email"><input type="email" required value={form.email} onChange={set('email')} /></Field>
        <Field label="Phone"><input required inputMode="numeric" maxLength={10} value={form.phone} onChange={set('phone')} /></Field>
        <Field label="Password" hint="8+ characters with upper, lower case and a digit">
          <input type="password" required value={form.password} onChange={set('password')} />
        </Field>
        <Field label="Company logo" hint="PNG, JPEG or WebP, up to 2 MB"><input type="file" accept="image/png,image/jpeg,image/webp" onChange={pickLogo} /></Field>
      </div>
      <Field label="Company profile"><textarea required rows={4} minLength={10} value={form.company_profile} onChange={set('company_profile')} /></Field>
      <button className="btn" disabled={busy}>{busy ? 'Submitting…' : 'Submit for verification'}</button>
      <p className="muted">Already approved? <Link to="/login">Sign in</Link></p>
    </form>
  )
}
