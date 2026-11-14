import { useCallback, useEffect, useState } from 'react'
import api, { errorMessage } from '../../api'
import Field from '../Field'
import { fmtDate } from '../student/format'

export default function AnnouncementsPanel() {
  const [rows, setRows] = useState(null)
  const [form, setForm] = useState({ id: null, title: '', body: '' })
  const [msg, setMsg] = useState(null)
  const load = useCallback(async () => { try { setRows((await api.get('/admin/announcements')).data) } catch (e) { setMsg({ ok: false, text: errorMessage(e) }) } }, [])
  useEffect(() => { load() }, [load])

  const save = async (e) => {
    e.preventDefault(); setMsg(null)
    const body = { title: form.title, body: form.body }
    try {
      if (form.id) await api.put(`/admin/announcements/${form.id}`, body); else await api.post('/announcements', body)
      setForm({ id: null, title: '', body: '' }); setMsg({ ok: true, text: 'Announcement saved and visible on the landing page' }); load()
    } catch (err) { setMsg({ ok: false, text: errorMessage(err) }) }
  }
  const remove = async (a) => {
    if (!window.confirm(`Delete “${a.title}”?`)) return
    try { await api.delete(`/admin/announcements/${a.id}`); setMsg({ ok: true, text: 'Announcement deleted' }); load() } catch (e) { setMsg({ ok: false, text: errorMessage(e) }) }
  }
  return (
    <div className="stack">
      <form className="card form wide" onSubmit={save}>
        <h3>{form.id ? 'Edit announcement' : 'New announcement'}</h3>
        <Field label="Title"><input required minLength={3} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
        <Field label="Message"><textarea required rows={3} minLength={3} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} /></Field>
        <div className="row"><button className="btn">{form.id ? 'Save changes' : 'Publish'}</button>{form.id && <button type="button" className="btn ghost" onClick={() => setForm({ id: null, title: '', body: '' })}>Cancel</button>}</div>
      </form>
      {msg && <div className={`alert ${msg.ok ? 'ok' : 'error'}`}>{msg.text}</div>}
      {rows?.length === 0 && <p className="muted">No announcements yet.</p>}
      {rows?.map((a) => (
        <div className="card job" key={a.id}>
          <div className="grow"><h3>{a.title}</h3><p>{a.body}</p><small className="muted">{fmtDate(a.created_at)}</small></div>
          <div className="actions stack"><button className="btn small outline" onClick={() => setForm({ id: a.id, title: a.title, body: a.body })}>Edit</button><button className="btn small danger" onClick={() => remove(a)}>Delete</button></div>
        </div>
      ))}
    </div>
  )
}
