import { useCallback, useEffect, useState } from 'react'
import api, { errorMessage } from '../../api'
import { fmtDate, fmtDateTime, openFile, StatusBadge } from './format'

export default function UpdatesPanel({ onChange }) {
  const [data, setData] = useState(null)
  const [msg, setMsg] = useState(null)

  const load = useCallback(async () => {
    try {
      const [drives, interviews, offers, attendance] = await Promise.all([
        api.get('/student/drives'), api.get('/student/interviews'), api.get('/student/offers'), api.get('/student/attendance'),
      ])
      setData({ drives: drives.data, interviews: interviews.data, offers: offers.data, attendance: attendance.data })
    } catch (e) { setMsg({ ok: false, text: errorMessage(e) }) }
  }, [])
  useEffect(() => { load() }, [load])

  const act = async (request, okText) => {
    setMsg(null)
    try { await request(); setMsg({ ok: true, text: okText }); await load(); onChange?.() } catch (e) { setMsg({ ok: false, text: errorMessage(e) }) }
  }
  const respond = (o, decision) => {
    const verb = decision === 'ACCEPT' ? 'accept' : 'decline'
    if (!window.confirm(`Really ${verb} the offer from ${o.company_name}?${decision === 'ACCEPT' ? ' You will be marked as placed and cannot accept another offer.' : ''}`)) return
    act(() => api.post(`/student/offers/${o.application_id}/respond`, { decision }),
      decision === 'ACCEPT' ? `Offer accepted: congratulations on joining ${o.company_name}!` : `Offer from ${o.company_name} declined`)
  }

  if (!data) return msg ? <div className="alert error">{msg.text}</div> : <p className="muted">Loading…</p>
  return (
    <div className="stack">
      {msg && <div className={`alert ${msg.ok ? 'ok' : 'error'}`}>{msg.text}</div>}
      <div className="card">
        <h3>Upcoming placement drives</h3>
        {data.drives.length === 0 && <p className="muted">No upcoming drives.</p>}
        {data.drives.map((d) => (
          <div className="item" key={d.id}>
            <div className="grow">
              <b>{d.title}</b> {d.eligible ? <span className="badge good">Eligible</span> : <span className="badge bad">Not eligible</span>}
              {d.registration_status && <> <span className="badge info">Registered</span></>}
              <p>{d.description}</p>
              <p className="muted">
                {fmtDateTime(d.drive_date)} · {d.venue} · Min CGPA {d.min_cgpa} · {d.departments.length ? d.departments.join(', ') : 'All departments'}
              </p>
              {!d.eligible && <p className="bad-text">{d.ineligible_reason}</p>}
            </div>
            {d.registration_status
              ? <button className="btn small outline" onClick={() => act(() => api.delete(`/student/drives/${d.id}/register`), `Registration for ${d.title} cancelled`)}>Cancel registration</button>
              : <button className="btn small" disabled={!d.eligible} onClick={() => act(() => api.post(`/student/drives/${d.id}/register`), `Registered for ${d.title}`)}>Register</button>}
          </div>
        ))}
      </div>

      <div className="card">
        <h3>My drive attendance</h3>
        {data.attendance.length === 0 && <p className="muted">You have not registered for any drive.</p>}
        {data.attendance.map((r) => (
          <div className="item" key={r.drive_id}>
            <div className="grow"><b>{r.title}</b> · {r.company_name}<p className="muted">{fmtDateTime(r.drive_date)}</p></div>
            <span className={`badge ${r.status === 'PRESENT' ? 'good' : r.status === 'ABSENT' ? 'bad' : 'info'}`}>
              {r.status === 'REGISTERED' ? 'Registered' : r.status === 'PRESENT' ? 'Present' : 'Absent'}
            </span>
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
              {o.has_file && <button className="link" onClick={() => openFile(`/student/offers/${o.application_id}/file`).catch((e) => setMsg({ ok: false, text: errorMessage(e) }))}>View offer letter (PDF)</button>}
            </div>
            <StatusBadge status={o.status} />
            {o.status === 'ISSUED' && (
              <div className="row">
                <button className="btn small" onClick={() => respond(o, 'ACCEPT')}>Accept</button>
                <button className="btn small danger" onClick={() => respond(o, 'DECLINE')}>Decline</button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
