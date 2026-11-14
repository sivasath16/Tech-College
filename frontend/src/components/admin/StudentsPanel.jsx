import { useCallback, useEffect, useState } from 'react'
import api, { errorMessage } from '../../api'
import { fmtDate, openFile, StatusBadge } from '../student/format'

function Detail({ id, onBack, onChange }) {
  const [d, setD] = useState(null)
  const [msg, setMsg] = useState(null)
  const load = useCallback(() => api.get(`/admin/students/${id}`).then((r) => setD(r.data)).catch((e) => setMsg({ ok: false, text: errorMessage(e) })), [id])
  useEffect(() => { load() }, [load])

  const act = async (fn, text) => {
    setMsg(null)
    try { await fn(); await load(); onChange(); setMsg({ ok: true, text }) } catch (e) { setMsg({ ok: false, text: errorMessage(e) }) }
  }
  if (!d) return <p className="muted">{msg ? msg.text : 'Loading…'}</p>
  const placed = d.placement_status === 'PLACED'
  return (
    <div className="stack">
      <div><button className="btn small ghost" onClick={onBack}>← Back to students</button></div>
      {msg && <div className={`alert ${msg.ok ? 'ok' : 'error'}`}>{msg.text}</div>}
      <div className="card">
        <div className="row between">
          <h3>{d.full_name} <span className="muted">· {d.college_id}</span></h3>
          <div className="row">
            <span className={`badge ${placed ? 'good' : 'info'}`}>{placed ? 'Placed' : 'Not placed'}</span>
            <span className={`badge ${d.is_active ? 'good' : 'bad'}`}>{d.is_active ? 'Active' : 'Deactivated'}</span>
          </div>
        </div>
        <dl className="dl">
          <dt>Email</dt><dd>{d.email}</dd><dt>Mobile</dt><dd>{d.mobile} {d.is_verified ? '✔ verified' : ''}</dd>
          <dt>Department</dt><dd>{d.department}</dd><dt>10th / 12th</dt><dd>{d.tenth_percent}% / {d.twelfth_percent}%</dd>
          <dt>Degree CGPA</dt><dd>{d.degree_cgpa}</dd><dt>Skills</dt><dd>{d.skills.join(', ') || '—'}</dd>
          <dt>Certifications</dt><dd>{d.certifications || '—'}{d.certificates.length > 0 && ` (${d.certificates.length} uploaded: ${d.certificates.map((c) => c.title).join(', ')})`}</dd>
        </dl>
        <div className="row top">
          {d.has_resume && <button className="btn small outline" onClick={() => openFile(`/admin/students/${id}/resume`).catch((e) => setMsg({ ok: false, text: errorMessage(e) }))}>View resume</button>}
          <button className="btn small outline" onClick={() => act(() => api.put(`/admin/students/${id}/placement-status`, { placement_status: placed ? 'NOT_PLACED' : 'PLACED' }), placed ? 'Marked not placed' : 'Marked placed')}>{placed ? 'Mark not placed' : 'Mark placed'}</button>
          <button className={`btn small ${d.is_active ? 'danger' : ''}`} onClick={() => act(() => api.patch(`/admin/students/${id}/active`, { is_active: !d.is_active }), d.is_active ? 'Account deactivated' : 'Account reactivated')}>{d.is_active ? 'Deactivate account' : 'Reactivate account'}</button>
        </div>
      </div>
      <div className="card">
        <h3>Applications ({d.applications.length})</h3>
        {d.applications.length === 0 && <p className="muted">No applications yet.</p>}
        {d.applications.map((a) => (
          <div className="item" key={a.id}><div className="grow"><b>{a.job_title}</b> <span className="muted">· {a.company_name} · applied {fmtDate(a.applied_at)}</span></div><StatusBadge status={a.status} /></div>
        ))}
      </div>
    </div>
  )
}

export default function StudentsPanel({ onChange }) {
  const [f, setF] = useState({ q: '', department: '', min_cgpa: '', placement_status: '', is_active: '' })
  const [rows, setRows] = useState(null)
  const [open, setOpen] = useState(null)
  const [error, setError] = useState('')
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const load = useCallback(async () => {
    const params = Object.fromEntries(Object.entries(f).filter(([, v]) => v !== ''))
    try { setRows((await api.get('/admin/students', { params })).data) } catch (e) { setError(errorMessage(e)) }
  }, [f])
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t) }, [load])

  if (open) return <Detail id={open} onBack={() => { setOpen(null); load() }} onChange={onChange} />
  return (
    <div className="stack">
      <div className="card">
        <h3>Student database</h3>
        <div className="cols">
          <label className="field"><span>Name, college ID or email</span><input value={f.q} onChange={set('q')} /></label>
          <label className="field"><span>Department</span><input value={f.department} onChange={set('department')} /></label>
          <label className="field"><span>Minimum CGPA</span><input type="number" step="0.1" min="0" max="10" value={f.min_cgpa} onChange={set('min_cgpa')} /></label>
          <label className="field"><span>Placement</span><select value={f.placement_status} onChange={set('placement_status')}><option value="">All</option><option value="PLACED">Placed</option><option value="NOT_PLACED">Not placed</option></select></label>
          <label className="field"><span>Account</span><select value={f.is_active} onChange={set('is_active')}><option value="">All</option><option value="true">Active</option><option value="false">Deactivated</option></select></label>
        </div>
      </div>
      {error && <div className="alert error">{error}</div>}
      <p className="muted">{rows ? `${rows.length} student${rows.length === 1 ? '' : 's'}` : 'Loading…'}</p>
      {rows?.length > 0 && (
        <div className="card scroll">
          <table>
            <thead><tr><th>College ID</th><th>Name</th><th>Department</th><th>CGPA</th><th>Email</th><th>Status</th><th /></tr></thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.id} className={s.is_active ? '' : 'dim'}>
                  <td>{s.college_id}</td><td>{s.full_name}</td><td>{s.department}</td><td>{s.degree_cgpa}</td><td>{s.email}</td>
                  <td><span className={`badge ${s.placement_status === 'PLACED' ? 'good' : 'info'}`}>{s.placement_status === 'PLACED' ? 'Placed' : 'Not placed'}</span>{!s.is_active && <> <span className="badge bad">Deactivated</span></>}</td>
                  <td><button className="btn small outline" onClick={() => setOpen(s.id)}>View</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
