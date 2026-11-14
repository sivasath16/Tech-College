import { useCallback, useEffect, useState } from 'react'
import api, { errorMessage } from '../../api'
import Field from '../Field'
import { fmtDateTime } from '../student/format'

const list = (s) => s.split(',').map((x) => x.trim()).filter(Boolean)
const local = (iso) => { const d = new Date(iso); const p = (n) => String(n).padStart(2, '0'); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}` }
const EMPTY = { title: '', company_name: '', description: '', venue: '', drive_date: '', min_cgpa: 0, departments: '', announce: true }

function DriveForm({ drive, onSaved, onCancel }) {
  const [f, setF] = useState(drive ? { ...drive, drive_date: local(drive.drive_date), departments: drive.departments.join(', '), announce: false } : EMPTY)
  const [error, setError] = useState('')
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const submit = async (e) => {
    e.preventDefault(); setError('')
    const body = { title: f.title, company_name: f.company_name, description: f.description, venue: f.venue, drive_date: new Date(f.drive_date).toISOString(), min_cgpa: Number(f.min_cgpa), departments: list(f.departments), announce: f.announce }
    try { onSaved((drive ? await api.put(`/admin/drives/${drive.id}`, body) : await api.post('/admin/drives', body)).data, !drive && f.announce) } catch (err) { setError(errorMessage(err)) }
  }
  return (
    <form className="card form wide" onSubmit={submit}>
      <h3>{drive ? `Edit: ${drive.title}` : 'Schedule a placement drive'}</h3>
      {error && <div className="alert error">{error}</div>}
      <div className="cols">
        <Field label="Drive title"><input required minLength={3} value={f.title} onChange={set('title')} /></Field>
        <Field label="Company"><input required value={f.company_name} onChange={set('company_name')} /></Field>
        <Field label="Date & time"><input type="datetime-local" required value={f.drive_date} onChange={set('drive_date')} /></Field>
        <Field label="Venue"><input required value={f.venue} onChange={set('venue')} /></Field>
        <Field label="Minimum CGPA"><input type="number" step="0.01" min="0" max="10" value={f.min_cgpa} onChange={set('min_cgpa')} /></Field>
        <Field label="Eligible departments" hint="Comma separated; empty = all"><input value={f.departments} onChange={set('departments')} /></Field>
      </div>
      <Field label="Details (rounds, documents to bring)"><textarea required rows={3} minLength={10} value={f.description} onChange={set('description')} /></Field>
      {!drive && <label className="check"><input type="checkbox" checked={f.announce} onChange={(e) => setF({ ...f, announce: e.target.checked })} /> Publish an announcement on the landing page</label>}
      <div className="row"><button className="btn">{drive ? 'Save changes' : 'Create drive'}</button><button type="button" className="btn ghost" onClick={onCancel}>Cancel</button></div>
    </form>
  )
}

export default function DrivesPanel({ onChange }) {
  const [rows, setRows] = useState(null)
  const [editing, setEditing] = useState(null)
  const [msg, setMsg] = useState(null)
  const load = useCallback(async () => { try { setRows((await api.get('/admin/drives')).data) } catch (e) { setMsg({ ok: false, text: errorMessage(e) }) } }, [])
  useEffect(() => { load() }, [load])

  const remove = async (d) => {
    if (!window.confirm(`Delete “${d.title}”?`)) return
    try { await api.delete(`/admin/drives/${d.id}`); setMsg({ ok: true, text: 'Drive deleted' }); load(); onChange() } catch (e) { setMsg({ ok: false, text: errorMessage(e) }) }
  }
  if (editing) return <DriveForm drive={editing === 'new' ? null : editing} onCancel={() => setEditing(null)} onSaved={(d, announced) => { setEditing(null); setMsg({ ok: true, text: `Saved “${d.title}”${announced ? ' and announced it on the landing page' : ''}` }); load(); onChange() }} />
  return (
    <div className="stack">
      <div className="row between"><h3>Placement drives</h3><button className="btn" onClick={() => setEditing('new')}>+ New drive</button></div>
      {msg && <div className={`alert ${msg.ok ? 'ok' : 'error'}`}>{msg.text}</div>}
      {rows?.length === 0 && <p className="muted">No drives scheduled.</p>}
      {rows?.map((d) => (
        <div className="card job" key={d.id}>
          <div className="grow">
            <h3>{d.title} <span className={`badge ${d.upcoming ? 'good' : 'info'}`}>{d.upcoming ? 'Upcoming' : 'Completed'}</span></h3>
            <p className="muted">{d.company_name} · {fmtDateTime(d.drive_date)} · {d.venue}</p>
            <p>{d.description}</p>
            <p className="muted">Min CGPA {d.min_cgpa} · Departments: {d.departments.join(', ') || 'All'}</p>
          </div>
          <div className="actions stack">
            <button className="btn small outline" onClick={() => setEditing(d)}>Edit</button>
            <button className="btn small danger" onClick={() => remove(d)}>Delete</button>
          </div>
        </div>
      ))}
    </div>
  )
}
