import { useCallback, useEffect, useState } from 'react'
import api, { errorMessage } from '../../api'
import { fmtDate, StatusBadge } from '../student/format'

const FILTERS = ['PENDING', 'APPROVED', 'REJECTED']

export default function JobsPanel({ onChange }) {
  const [tab, setTab] = useState('PENDING')
  const [rows, setRows] = useState(null)
  const [msg, setMsg] = useState(null)
  const load = useCallback(async () => {
    try { setRows((await api.get('/admin/jobs')).data) } catch (e) { setMsg({ ok: false, text: errorMessage(e) }) }
  }, [])
  useEffect(() => { load() }, [load])

  const decide = async (j, action) => {
    setMsg(null)
    try {
      if (action === 'reject') {
        const reason = window.prompt('Reason for rejection (shown to the recruiter)?')
        if (!reason) return
        await api.post(`/admin/jobs/${j.id}/reject`, { reason })
      } else await api.post(`/admin/jobs/${j.id}/approve`)
      setMsg({ ok: true, text: action === 'approve' ? `“${j.title}” is now published to students` : `“${j.title}” rejected` })
      load(); onChange()
    } catch (e) { setMsg({ ok: false, text: errorMessage(e) }) }
  }
  const count = (s) => (rows || []).filter((j) => j.verification_status === s).length
  const shown = (rows || []).filter((j) => j.verification_status === tab)
  return (
    <div className="card">
      <h3>Job posting verification</h3>
      <p className="muted">Approving a posting publishes it to students. Recruiters who edit a published posting send it back here.</p>
      <div className="tabs">{FILTERS.map((f) => <button key={f} className={`tab ${tab === f ? 'active' : ''}`} onClick={() => setTab(f)}>{f} ({count(f)})</button>)}</div>
      {msg && <div className={`alert ${msg.ok ? 'ok' : 'error'}`}>{msg.text}</div>}
      {rows && shown.length === 0 && <p className="muted">No {tab.toLowerCase()} postings.</p>}
      {shown.map((j) => (
        <div className="item" key={j.id}>
          <div className="grow">
            <b>{j.title}</b> <span className={`badge ${j.job_type === 'JOB' ? 'info' : 'warn'}`}>{j.job_type === 'JOB' ? 'Job' : 'Internship'}</span> {!j.is_active && <span className="badge bad">Closed</span>}
            <p className="muted">{j.company_name} · {j.location}{j.salary && ` · ${j.salary}`} · Min CGPA {j.min_cgpa} · Apply by {fmtDate(j.deadline)}</p>
            <p>{j.description}</p>
            <p className="muted">Skills: {j.required_skills.join(', ') || '—'} · Departments: {j.eligible_departments.join(', ') || 'All'} · {j.applicants} applicants</p>
            {j.rejection_reason && <small className="muted">Rejected: {j.rejection_reason}</small>}
          </div>
          {tab === 'PENDING'
            ? <div className="row"><button className="btn small" onClick={() => decide(j, 'approve')}>Approve &amp; publish</button><button className="btn small danger" onClick={() => decide(j, 'reject')}>Reject</button></div>
            : <StatusBadge status={j.verification_status} />}
        </div>
      ))}
    </div>
  )
}
