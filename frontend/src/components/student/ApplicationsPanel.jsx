import { useEffect, useState } from 'react'
import api, { errorMessage } from '../../api'
import { fmtDate, fmtDateTime, StatusBadge, Tracker } from './format'

export default function ApplicationsPanel() {
  const [apps, setApps] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    api.get('/student/applications').then((r) => setApps(r.data)).catch((e) => setError(errorMessage(e)))
  }, [])

  if (error) return <div className="alert error">{error}</div>
  if (!apps) return <p className="muted">Loading…</p>
  if (!apps.length) return <p className="muted">You have not applied to anything yet. Browse the Jobs tab to get started.</p>
  return (
    <div className="stack">
      {apps.map((a) => (
        <div className="card" key={a.id}>
          <div className="row between">
            <div>
              <h3>{a.job_title}</h3>
              <p className="muted">{a.company_name} · {a.job_type === 'JOB' ? 'Job' : 'Internship'} · applied {fmtDate(a.applied_at)}</p>
            </div>
            <StatusBadge status={a.status} />
          </div>
          <Tracker status={a.status} />
          {a.interviews.map((i) => (
            <p key={i.id} className="note">Interview: {fmtDateTime(i.scheduled_at)} · {i.mode} · {i.location}{i.notes && ` — ${i.notes}`}</p>
          ))}
          {a.offer && <p className="note">Offer letter: <StatusBadge status={a.offer.status} /> {a.offer.package && `· ${a.offer.package}`}</p>}
        </div>
      ))}
    </div>
  )
}
