import { useState } from 'react'
import api, { API_URL, errorMessage } from '../../api'
import Field from '../Field'
import { useAuth } from '../../context/AuthContext'

export default function ProfilePanel() {
  const { user, reload } = useAuth()
  const r = user.recruiter
  const [form, setForm] = useState({
    company_name: r.company_name, contact_person: r.contact_person, phone: r.phone, company_profile: r.company_profile,
  })
  const [msg, setMsg] = useState(null)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const save = async (e) => {
    e.preventDefault(); setMsg(null)
    try {
      await api.put('/recruiter/profile', form)
      await reload()
      setMsg({ ok: true, text: 'Company profile saved' })
    } catch (err) { setMsg({ ok: false, text: errorMessage(err) }) }
  }

  const changeLogo = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setMsg(null)
    const data = new FormData()
    data.append('logo', file)
    try {
      await api.post('/recruiter/logo', data)
      await reload()
      setMsg({ ok: true, text: 'Logo updated' })
    } catch (err) { setMsg({ ok: false, text: errorMessage(err) }) }
    e.target.value = ''
  }

  return (
    <form className="card form wide" onSubmit={save}>
      <h3>Company profile</h3>
      <div className="row">
        {r.logo_path ? <img className="logo" src={`${API_URL}/media/${r.logo_path}`} alt="Company logo" /> : <div className="logo" />}
        <Field label="Replace logo" hint="PNG, JPEG or WebP, up to 2 MB">
          <input className="file" type="file" accept="image/png,image/jpeg,image/webp" onChange={changeLogo} />
        </Field>
      </div>
      {msg && <div className={`alert ${msg.ok ? 'ok' : 'error'}`}>{msg.text}</div>}
      <div className="cols">
        <Field label="Company name"><input required value={form.company_name} onChange={set('company_name')} /></Field>
        <Field label="Contact person"><input required value={form.contact_person} onChange={set('contact_person')} /></Field>
        <Field label="Phone"><input required inputMode="numeric" maxLength={10} value={form.phone} onChange={set('phone')} /></Field>
        <Field label="Login email" hint="Contact the placement cell to change it"><input value={user.email} disabled /></Field>
      </div>
      <Field label="Company profile"><textarea required rows={5} minLength={10} value={form.company_profile} onChange={set('company_profile')} /></Field>
      <div><button className="btn">Save profile</button></div>
    </form>
  )
}
