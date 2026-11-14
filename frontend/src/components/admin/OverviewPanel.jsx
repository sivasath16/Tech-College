import { useEffect, useState } from 'react'
import api from '../../api'
import { fmtDateTime, label } from '../student/format'

const Stat = ({ title, value, tone }) => (
  <div className="card stat"><span className="muted">{title}</span><b className={tone}>{value ?? '—'}</b></div>
)

export default function OverviewPanel({ summary, go }) {
  const [logs, setLogs] = useState([])
  useEffect(() => { api.get('/admin/audit-logs', { params: { limit: 8 } }).then((r) => setLogs(r.data)).catch(() => {}) }, [summary])
  const by = summary?.applications_by_status || {}
  const max = Math.max(1, ...Object.values(by))

  return (
    <div className="stack">
      <div className="grid3">
        <Stat title="Registered students" value={summary?.students} />
        <Stat title="Placed" value={summary && `${summary.placed} (${summary.placement_percent}%)`} tone="good" />
        <Stat title="Recruiters awaiting approval" value={summary?.recruiters_pending} tone={summary?.recruiters_pending ? 'warn-text' : ''} />
        <Stat title="Job posts awaiting verification" value={summary?.jobs_pending} tone={summary?.jobs_pending ? 'warn-text' : ''} />
        <Stat title="Published openings" value={summary?.jobs_published} />
        <Stat title="Upcoming drives" value={summary?.drives_upcoming} />
      </div>
      <div className="row top">
        {(summary?.recruiters_pending > 0) && <button className="btn small" onClick={() => go('recruiters')}>Review recruiters</button>}
        {(summary?.jobs_pending > 0) && <button className="btn small" onClick={() => go('jobs')}>Verify job posts</button>}
      </div>
      <div className="card">
        <h3>Applications by stage ({summary?.applications ?? 0})</h3>
        {Object.entries(by).map(([k, v]) => (
          <div className="hbar" key={k}><span>{label(k)}</span><div className="bar"><span style={{ width: `${(v / max) * 100}%` }} /></div><b>{v}</b></div>
        ))}
      </div>
      <div className="card">
        <h3>Recent admin activity</h3>
        {logs.length === 0 && <p className="muted">No activity recorded yet.</p>}
        {logs.map((l) => (
          <p className="logline" key={l.id}><b>{label(l.action)}</b> <span className="muted">· {l.entity_type} #{l.entity_id} · {l.admin_email} · {fmtDateTime(l.created_at)}</span></p>
        ))}
      </div>
    </div>
  )
}
