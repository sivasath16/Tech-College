import { useEffect, useState } from 'react'
import api, { errorMessage } from '../../api'
import { fmtDate, fmtDateTime, StatusBadge } from './format'

export default function UpdatesPanel() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    Promise.all([api.get('/student/drives'), api.get('/student/interviews'), api.get('/student/offers')])
      .then(([drives, interviews, offers]) => setData({ drives: drives.data, interviews: interviews.data, offers: offers.data }))
      .catch((e) => setError(errorMessage(e)))
  }, [])

  if (error) return <div className="alert error">{error}</div>
  if (!data) return <p className="muted">Loading…</p>
  return (
    <div className="stack">
      <div className="card">
        <h3>Upcoming placement drives</h3>
        {data.drives.length === 0 && <p className="muted">No upcoming drives.</p>}
        {data.drives.map((d) => (
          <div className="item" key={d.id}>
            <div className="grow">
              <b>{d.title}</b> {d.eligible ? <span className="badge good">Eligible</span> : <span className="badge bad">Not eligible</span>}
              <p>{d.description}</p>
              <p className="muted">
                {fmtDateTime(d.drive_date)} · {d.venue} · Min CGPA {d.min_cgpa} · {d.departments.length ? d.departments.join(', ') : 'All departments'}
              </p>
              {!d.eligible && <p className="bad-text">{d.ineligible_reason}</p>}
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <h3>Interview updates</h3>
        {data.interviews.length === 0 && <p className="muted">No interviews scheduled.</p>}
        {data.interviews.map((i, n) => (
          <div className="item" key={n}>
            <div className="grow">
              <b>{i.job_title}</b> · {i.company_name}
              <p>{fmtDateTime(i.scheduled_at)} · {i.mode} · {i.location}</p>
              {i.notes && <p className="muted">{i.notes}</p>}
            </div>
            {new Date(i.scheduled_at) >= new Date() ? <span className="badge warn">Upcoming</span> : <span className="badge info">Completed</span>}
          </div>
        ))}
      </div>

      <div className="card">
        <h3>Offer letters</h3>
        {data.offers.length === 0 && <p className="muted">No offers yet.</p>}
        {data.offers.map((o) => (
          <div className="item" key={o.application_id}>
            <div className="grow">
              <b>{o.job_title}</b> · {o.company_name}
              <p className="muted">{o.package && `Package ${o.package}`}{o.joining_date && ` · Joining ${fmtDate(o.joining_date)}`}</p>
            </div>
            <StatusBadge status={o.status} />
          </div>
        ))}
      </div>
    </div>
  )
}
