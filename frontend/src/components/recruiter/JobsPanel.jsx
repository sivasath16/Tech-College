import { useCallback, useEffect, useState } from 'react'
import api, { errorMessage } from '../../api'
import { fmtDate } from '../student/format'
import JobForm from './JobForm'

export default function JobsPanel({ onChange, onReview }) {
  const [jobs, setJobs] = useState(null)
  const [editing, setEditing] = useState(null) // null | 'new' | job
  const [msg, setMsg] = useState(null)

  const load = useCallback(async () => {
    try { setJobs((await api.get('/recruiter/jobs')).data) } catch (err) { setMsg({ ok: false, text: errorMessage(err) }) }
  }, [])
  useEffect(() => { load() }, [load])

  const toggle = async (job) => {
    setMsg(null)
    try {
      await api.post(`/recruiter/jobs/${job.id}/${job.is_active ? 'close' : 'reopen'}`)
      load(); onChange?.()
    } catch (err) { setMsg({ ok: false, text: errorMessage(err) }) }
  }

  if (editing) {
    return <JobForm job={editing === 'new' ? null : editing} onCancel={() => setEditing(null)}
      onSaved={(j) => { setEditing(null); setMsg({ ok: true, text: `Saved “${j.title}” — sent to the placement cell for verification` }); load(); onChange?.() }} />
  }

  return (
    <div className="stack">
      <div className="row between"><h3>Your postings</h3><button className="btn" onClick={() => setEditing('new')}>+ New posting</button></div>
      {msg && <div className={`alert ${msg.ok ? 'ok' : 'error'}`}>{msg.text}</div>}
      {jobs === null && <p className="muted">Loading…</p>}
      {jobs?.length === 0 && <p className="muted">No postings yet. Create your first job or internship.</p>}
      {jobs?.map((j) => {
        const state = j.verification_status === 'PENDING' ? ['Awaiting verification', 'warn']
          : j.verification_status === 'REJECTED' ? ['Rejected', 'bad']
          : !j.is_active ? ['Closed', 'bad'] : j.expired ? ['Expired', 'warn'] : ['Published', 'good']
        return (
          <div className="card job" key={j.id}>
            <div className="grow">
              <h3>{j.title} <span className={`badge ${j.job_type === 'JOB' ? 'info' : 'warn'}`}>{j.job_type === 'JOB' ? 'Job' : 'Internship'}</span> <span className={`badge ${state[1]}`}>{state[0]}</span></h3>
              <p className="muted">{j.location}{j.salary && ` · ${j.salary}`} · Min CGPA {j.min_cgpa} · Apply by {fmtDate(j.deadline)}</p>
              <p className="muted">Skills: {j.required_skills.join(', ') || '—'} · Departments: {j.eligible_departments.join(', ') || 'All'}</p>
              {j.verification_status === 'REJECTED' && <p className="bad-text">Placement cell: {j.rejection_reason}. Edit the posting to resubmit it.</p>}
              {j.verification_status === 'PENDING' && <p className="muted">Students see this posting once the placement cell approves it.</p>}
              <p><b>{j.applicants}</b> applicants · <b>{j.shortlisted}</b> shortlisted · <b>{j.selected}</b> selected</p>
            </div>
            <div className="actions stack">
              <button className="btn small" onClick={() => onReview(j.id)}>Review applicants</button>
              <button className="btn small outline" onClick={() => setEditing(j)}>Edit</button>
              <button className="btn small ghost" onClick={() => toggle(j)}>{j.is_active ? 'Close posting' : 'Reopen'}</button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
