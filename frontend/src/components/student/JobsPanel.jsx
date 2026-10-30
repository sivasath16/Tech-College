import { useCallback, useEffect, useState } from 'react'
import api, { API_URL, errorMessage } from '../../api'
import { fmtDate, StatusBadge } from './format'

const TYPES = [['', 'All'], ['JOB', 'Jobs'], ['INTERNSHIP', 'Internships']]

export default function JobsPanel({ onApplied }) {
  const [jobs, setJobs] = useState(null)
  const [type, setType] = useState('')
  const [q, setQ] = useState('')
  const [msg, setMsg] = useState(null)
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('/student/jobs', { params: { job_type: type || undefined, q: q || undefined } })
      setJobs(data)
    } catch (err) { setMsg({ ok: false, text: errorMessage(err) }) }
  }, [type, q])
  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t) }, [load])

  const apply = async (job) => {
    setMsg(null); setBusyId(job.id)
    try {
      await api.post('/student/applications', { job_id: job.id })
      setMsg({ ok: true, text: `Applied to ${job.title} at ${job.company_name}` })
      await load()
      onApplied?.()
    } catch (err) { setMsg({ ok: false, text: errorMessage(err) }) } finally { setBusyId(null) }
  }

  return (
    <div className="stack">
      <div className="row">
        <div className="tabs">
          {TYPES.map(([v, l]) => <button key={l} className={`tab ${type === v ? 'active' : ''}`} onClick={() => setType(v)}>{l}</button>)}
        </div>
        <input className="search" placeholder="Search title, company or location" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      {msg && <div className={`alert ${msg.ok ? 'ok' : 'error'}`}>{msg.text}</div>}
      {jobs === null && <p className="muted">Loading…</p>}
      {jobs?.length === 0 && <p className="muted">No openings match.</p>}
      {jobs?.map((j) => (
        <div className="card job" key={j.id}>
          {j.company_logo
            ? <img className="logo small" src={`${API_URL}/media/${j.company_logo}`} alt="" />
            : <div className="logo small" />}
          <div className="grow">
            <h3>{j.title} <span className={`badge ${j.job_type === 'JOB' ? 'info' : 'warn'}`}>{j.job_type === 'JOB' ? 'Job' : 'Internship'}</span></h3>
            <p className="muted">{j.company_name} · {j.location}{j.salary && ` · ${j.salary}`}</p>
            <p>{j.description}</p>
            <p className="muted">
              Skills: {j.required_skills.join(', ') || '—'} · Min CGPA {j.min_cgpa} · Apply by {fmtDate(j.deadline)}
            </p>
            {!j.eligible && <p className="bad-text">Not eligible: {j.ineligible_reason}</p>}
          </div>
          <div className="actions">
            {j.application_status
              ? <StatusBadge status={j.application_status} />
              : <button className="btn" disabled={!j.eligible || busyId === j.id} onClick={() => apply(j)}>{busyId === j.id ? 'Applying…' : 'Apply'}</button>}
          </div>
        </div>
      ))}
    </div>
  )
}
