import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api, { errorMessage } from '../api'
import Field from '../components/Field'

const empty = {
  college_id: '', full_name: '', email: '', mobile: '', password: '', department: '',
  tenth_percent: '', twelfth_percent: '', degree_cgpa: '', skills: '', certifications: '',
}

export default function RegisterStudent() {
  const navigate = useNavigate()
  const [form, setForm] = useState(empty)
  const [otp, setOtp] = useState({ code: '', sent: false, verified: false, dev: '' })
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const sendOtp = async () => {
    setError(''); setInfo('')
    try {
      const { data } = await api.post('/auth/otp/send', { mobile: form.mobile })
      setOtp({ ...otp, sent: true, verified: false, dev: data.dev_otp || '' })
      setInfo(`OTP sent. It expires in ${data.expires_in_minutes} minutes.`)
    } catch (err) { setError(errorMessage(err)) }
  }

  const verifyOtp = async () => {
    setError(''); setInfo('')
    try {
      await api.post('/auth/otp/verify', { mobile: form.mobile, code: otp.code })
      setOtp({ ...otp, verified: true })
      setInfo('Mobile number verified ✔')
    } catch (err) { setError(errorMessage(err)) }
  }

  const submit = async (e) => {
    e.preventDefault()
    setError(''); setBusy(true)
    try {
      await api.post('/auth/register/student', {
        ...form,
        tenth_percent: Number(form.tenth_percent),
        twelfth_percent: Number(form.twelfth_percent),
        degree_cgpa: Number(form.degree_cgpa),
        skills: form.skills.split(',').map((s) => s.trim()).filter(Boolean),
        certifications: form.certifications || null,
      })
      navigate('/login', { state: { registered: true } })
    } catch (err) { setError(errorMessage(err)) } finally { setBusy(false) }
  }

  return (
    <form className="card form" onSubmit={submit}>
      <h2>Student registration</h2>
      {error && <div className="alert error">{error}</div>}
      {info && <div className="alert ok">{info}</div>}

      <h3>Account</h3>
      <div className="cols">
        <Field label="College ID"><input required value={form.college_id} onChange={set('college_id')} /></Field>
        <Field label="Full name"><input required value={form.full_name} onChange={set('full_name')} /></Field>
        <Field label="Email"><input type="email" required value={form.email} onChange={set('email')} /></Field>
        <Field label="Password" hint="8+ characters with upper, lower case and a digit">
          <input type="password" required value={form.password} onChange={set('password')} />
        </Field>
      </div>

      <h3>Mobile verification</h3>
      <div className="cols">
        <Field label="Mobile number"><input required inputMode="numeric" maxLength={10} value={form.mobile} onChange={set('mobile')} disabled={otp.verified} /></Field>
        <div className="otp">
          <button type="button" className="btn outline" onClick={sendOtp} disabled={otp.verified || form.mobile.length !== 10}>
            {otp.sent ? 'Resend OTP' : 'Send OTP'}
          </button>
          {otp.sent && !otp.verified && (
            <>
              <input placeholder="6-digit OTP" maxLength={6} value={otp.code} onChange={(e) => setOtp({ ...otp, code: e.target.value })} />
              <button type="button" className="btn" onClick={verifyOtp} disabled={otp.code.length !== 6}>Verify</button>
            </>
          )}
        </div>
      </div>
      {otp.dev && !otp.verified && <small className="muted">Development mode: mock SMS OTP is <b>{otp.dev}</b></small>}

      <h3>Academic profile</h3>
      <div className="cols">
        <Field label="Department"><input required value={form.department} onChange={set('department')} /></Field>
        <Field label="10th %"><input type="number" step="0.01" min="0" max="100" required value={form.tenth_percent} onChange={set('tenth_percent')} /></Field>
        <Field label="12th %"><input type="number" step="0.01" min="0" max="100" required value={form.twelfth_percent} onChange={set('twelfth_percent')} /></Field>
        <Field label="Degree CGPA"><input type="number" step="0.01" min="0" max="10" required value={form.degree_cgpa} onChange={set('degree_cgpa')} /></Field>
      </div>
      <Field label="Skills" hint="Comma separated, e.g. Python, SQL, React"><input value={form.skills} onChange={set('skills')} /></Field>
      <Field label="Certifications"><textarea rows={2} value={form.certifications} onChange={set('certifications')} /></Field>

      <button className="btn" disabled={busy || !otp.verified}>{busy ? 'Creating account…' : 'Create account'}</button>
      {!otp.verified && <small className="muted">Verify your mobile number to enable registration.</small>}
      <p className="muted">Already registered? <Link to="/login">Sign in</Link></p>
    </form>
  )
}
