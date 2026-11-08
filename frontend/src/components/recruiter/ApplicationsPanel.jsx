import { useCallback, useEffect, useState } from 'react'
import api, { errorMessage } from '../../api'
import { fmtDateTime, openFile, StatusBadge, Tracker } from '../student/format'

const STATUSES = ['', 'APPLIED', 'SHORTLISTED', 'INTERVIEW_SCHEDULED', 'INTERVIEWED', 'SELECTED', 'REJECTED']

function InterviewForm({ id, onDone, onCancel }) {
  const [form, setForm] = useState({ scheduled_at: '', mode: 'Online', location: '', notes: '' })
  const [error, setError] = useState('')
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const submit = async (e) => {
    e.preventDefault(); setError('')
    try {
      await api.post(`/recruiter/applications/${id}/interviews`, {
        ...form, scheduled_at: new Date(form.scheduled_at).toISOString(), notes: form.notes || null,
      })
      onDone()
    } catch (err) { setError(errorMessage(err)) }
  }
  return (
    <form className="note stack" onSubmit={submit}>
      {error && <div className="alert error">{error}</div>}
      <div className="cols">
        <label className="field"><span>Date & time</span><input type="datetime-local" required value={form.scheduled_at} onChange={set('scheduled_at')} /></label>
        <label className="field"><span>Mode</span><select value={form.mode} onChange={set('mode')}><option>Online</option><option>Offline</option></select></label>
        <label className="field"><span>{form.mode === 'Online' ? 'Meeting link' : 'Venue'}</span><input required minLength={2} value={form.location} onChange={set('location')} /></label>
      </div>
      <label className="field"><span>Notes for the candidate</span><input value={form.notes} onChange={set('notes')} /></label>
      <div className="row"><button className="btn small">Schedule interview</button><button type="button" className="btn small ghost" onClick={onCancel}>Cancel</button></div>
    </form>
  )
}

export default function ApplicationsPanel({ jobId, onChange }) {
  const [jobs, setJobs] = useState([])
  const [job, setJob] = useState(jobId || '')
  const [status, setStatus] = useState('')
  const [rows, setRows] = useState(null)
  const [scheduling, setScheduling] = useState(null)
  const [msg, setMsg] = useState(null)

  useEffect(() => { api.get('/recruiter/jobs').then((r) => setJobs(r.data)).catch(() => {}) }, [])
  useEffect(() => { setJob(jobId || '') }, [jobId])

  const load = useCallback(async () => {
    try {
      const params = { job_id: job || undefined, status_filter: status || undefined }
      setRows((await api.get('/recruiter/applications', { params })).data)
    } catch (err) { setMsg({ ok: false, text: errorMessage(err) }) }
  }, [job, status])
  useEffect(() => { load() }, [load])

  const move = async (a, next) => {
    setMsg(null)
    try {
      await api.patch(`/recruiter/applications/${a.id}/status`, { status: next })
      setMsg({ ok: true, text: `${a.student.full_name} marked ${next.replaceAll('_', ' ').toLowerCase()}` })
      load(); onChange?.()
    } catch (err) { setMsg({ ok: false, text: errorMessage(err) }) }
  }

  return (
    <div className="stack">
      <div className="row">
        <label className="field"><span>Posting</span>
          <select value={job} onChange={(e) => setJob(e.target.value)}>
            <option value="">All postings</option>
            {jobs.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
          </select>
        </label>
        <label className="field"><span>Status</span>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            {STATUSES.map((s) => <option key={s} value={s}>{s ? s.replaceAll('_', ' ') : 'All statuses'}</option>)}
          </select>
        </label>
      </div>
      {msg && <div className={`alert ${msg.ok ? 'ok' : 'error'}`}>{msg.text}</div>}
      {rows === null && <p className="muted">Loading…</p>}
      {rows?.length === 0 && <p className="muted">No applications match.</p>}
      {rows?.map((a) => (
        <div className="card" key={a.id}>
          <div className="row between">
            <div>
              <h3>{a.student.full_name} <span className="muted">· {a.student.college_id}</span></h3>
              <p className="muted">Applied for <b>{a.job_title}</b> · {a.student.department} · CGPA {a.student.degree_cgpa}</p>
            </div>
            <StatusBadge status={a.status} />
          </div>
          <p className="muted">{a.email} · {a.mobile}</p>
          <p>Skills: {a.student.skills.join(', ') || '—'}{a.skills_match.length > 0 && <> · <span className="good">matches {a.skills_match.join(', ')}</span></>}</p>
          <Tracker status={a.status} />
          {a.interviews.map((i) => <p className="note" key={i.id}>🗓 {fmtDateTime(i.scheduled_at)} · {i.mode} · {i.location}{i.notes && ` — ${i.notes}`}</p>)}
          <div className="row">
            {a.student.has_resume && <button className="btn small outline" onClick={() => openFile(`/recruiter/applications/${a.id}/resume`).catch((e) => setMsg({ ok: false, text: errorMessage(e) }))}>View resume</button>}
            {a.status === 'APPLIED' && <button className="btn small" onClick={() => move(a, 'SHORTLISTED')}>Shortlist</button>}
            {['SHORTLISTED', 'INTERVIEW_SCHEDULED', 'INTERVIEWED'].includes(a.status) && <button className="btn small" onClick={() => setScheduling(a.id)}>{a.status === 'SHORTLISTED' ? 'Schedule interview' : 'Add interview round'}</button>}
            {a.status === 'INTERVIEW_SCHEDULED' && <button className="btn small" onClick={() => move(a, 'INTERVIEWED')}>Mark interviewed</button>}
            {a.status === 'INTERVIEWED' && <button className="btn small" onClick={() => move(a, 'SELECTED')}>Select</button>}
            {!['SELECTED', 'REJECTED'].includes(a.status) && <button className="btn small danger" onClick={() => move(a, 'REJECTED')}>Reject</button>}
          </div>
          {scheduling === a.id && <InterviewForm id={a.id} onCancel={() => setScheduling(null)} onDone={() => { setScheduling(null); setMsg({ ok: true, text: 'Interview scheduled' }); load(); onChange?.() }} />}
        </div>
      ))}
    </div>
  )
}
