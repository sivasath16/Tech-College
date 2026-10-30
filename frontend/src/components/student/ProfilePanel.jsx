import { useState } from 'react'
import api, { errorMessage } from '../../api'
import { useAuth } from '../../context/AuthContext'
import Field from '../Field'

export default function ProfilePanel() {
  const { user, reload } = useAuth()
  const s = user.student
  const [form, setForm] = useState({
    full_name: s.full_name, department: s.department, tenth_percent: s.tenth_percent,
    twelfth_percent: s.twelfth_percent, degree_cgpa: s.degree_cgpa, skills: s.skills.join(', '),
    certifications: s.certifications || '',
  })
  const [msg, setMsg] = useState(null)
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const save = async (e) => {
    e.preventDefault()
    setMsg(null); setBusy(true)
    try {
      await api.put('/student/profile', {
        ...form,
        tenth_percent: Number(form.tenth_percent),
        twelfth_percent: Number(form.twelfth_percent),
        degree_cgpa: Number(form.degree_cgpa),
        skills: form.skills.split(',').map((x) => x.trim()).filter(Boolean),
        certifications: form.certifications || null,
      })
      await reload()
      setMsg({ ok: true, text: 'Profile updated' })
    } catch (err) { setMsg({ ok: false, text: errorMessage(err) }) } finally { setBusy(false) }
  }

  return (
    <form className="card form wide" onSubmit={save}>
      <h3>Personal</h3>
      <div className="cols">
        <Field label="Full name"><input required value={form.full_name} onChange={set('full_name')} /></Field>
        <Field label="Department"><input required value={form.department} onChange={set('department')} /></Field>
        <Field label="College ID" hint="Cannot be changed"><input value={s.college_id} disabled /></Field>
        <Field label="Email" hint="Cannot be changed"><input value={user.email} disabled /></Field>
      </div>
      <h3>Academic details</h3>
      <div className="cols">
        <Field label="10th %"><input type="number" step="0.01" min="0" max="100" required value={form.tenth_percent} onChange={set('tenth_percent')} /></Field>
        <Field label="12th %"><input type="number" step="0.01" min="0" max="100" required value={form.twelfth_percent} onChange={set('twelfth_percent')} /></Field>
        <Field label="Degree CGPA"><input type="number" step="0.01" min="0" max="10" required value={form.degree_cgpa} onChange={set('degree_cgpa')} /></Field>
      </div>
      <Field label="Skills" hint="Comma separated, e.g. Python, SQL, React"><input value={form.skills} onChange={set('skills')} /></Field>
      <Field label="Certifications" hint="Summary shown to recruiters. Upload the files under Documents."><textarea rows={2} value={form.certifications} onChange={set('certifications')} /></Field>
      {msg && <div className={`alert ${msg.ok ? 'ok' : 'error'}`}>{msg.text}</div>}
      <div><button className="btn" disabled={busy}>{busy ? 'Saving…' : 'Save changes'}</button></div>
    </form>
  )
}
