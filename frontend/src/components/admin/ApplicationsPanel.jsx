import { useCallback, useEffect, useState } from 'react'
import api, { errorMessage } from '../../api'
import { fmtDate, StatusBadge } from '../student/format'

const STATUSES = ['', 'APPLIED', 'SHORTLISTED', 'INTERVIEW_SCHEDULED', 'INTERVIEWED', 'SELECTED', 'REJECTED']

export default function ApplicationsPanel({ onChange }) {
  const [f, setF] = useState({ status_filter: '', company: '', department: '' })
  const [rows, setRows] = useState(null)
  const [msg, setMsg] = useState(null)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const load = useCallback(async () => {
    const params = Object.fromEntries(Object.entries(f).filter(([, v]) => v !== ''))
    try { setRows((await api.get('/admin/applications', { params })).data) } catch (e) { setMsg({ ok: false, text: errorMessage(e) }) }
  }, [f])
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t) }, [load])

  const confirm = async (a) => {
    setMsg(null)
    try { await api.post(`/admin/applications/${a.id}/confirm-placement`); setMsg({ ok: true, text: `${a.student_name} confirmed as placed at ${a.company_name}` }); load(); onChange() } catch (e) { setMsg({ ok: false, text: errorMessage(e) }) }
  }
  return (
    <div className="stack">
      <div className="card">
        <h3>Application tracking &amp; selections</h3>
        <div className="cols">
          <label className="field"><span>Stage</span><select value={f.status_filter} onChange={set('status_filter')}>{STATUSES.map((s) => <option key={s} value={s}>{s ? s.replaceAll('_', ' ') : 'All stages'}</option>)}</select></label>
          <label className="field"><span>Company</span><input value={f.company} onChange={set('company')} /></label>
          <label className="field"><span>Department</span><input value={f.department} onChange={set('department')} /></label>
        </div>
      </div>
      {msg && <div className={`alert ${msg.ok ? 'ok' : 'error'}`}>{msg.text}</div>}
      <p className="muted">{rows ? `${rows.length} application${rows.length === 1 ? '' : 's'}` : 'Loading…'}</p>
      {rows?.length > 0 && (
        <div className="card scroll">
          <table>
            <thead><tr><th>Student</th><th>Department</th><th>Position</th><th>Applied</th><th>Stage</th><th /></tr></thead>
            <tbody>
              {rows.map((a) => (
                <tr key={a.id}>
                  <td><b>{a.student_name}</b><br /><span className="muted">{a.college_id} · CGPA {a.degree_cgpa}</span></td>
                  <td>{a.department}</td>
                  <td>{a.job_title}<br /><span className="muted">{a.company_name}</span></td>
                  <td>{fmtDate(a.applied_at)}</td>
                  <td><StatusBadge status={a.status} />{a.placement_status === 'PLACED' && <> <span className="badge good">Placed</span></>}</td>
                  <td>{a.status === 'SELECTED' && a.placement_status !== 'PLACED' && <button className="btn small" onClick={() => confirm(a)}>Confirm placement</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
