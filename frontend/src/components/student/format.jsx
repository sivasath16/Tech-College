import api from '../../api'

export const label = (s) => s.replaceAll('_', ' ').toLowerCase().replace(/^\w|\s\w/g, (c) => c.toUpperCase())
// Date-only values (YYYY-MM-DD) are calendar dates: parse as local so they do not shift a day in western time zones.
const parseDate = (d) => (/^\d{4}-\d{2}-\d{2}$/.test(d) ? new Date(...d.split('-').map((n, i) => (i === 1 ? n - 1 : +n))) : new Date(d))
export const fmtDate = (d) => parseDate(d).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
export const fmtDateTime = (d) =>
  new Date(d).toLocaleString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })

const TONE = {
  APPLIED: 'info', SHORTLISTED: 'warn', INTERVIEW_SCHEDULED: 'warn', INTERVIEWED: 'warn',
  SELECTED: 'good', REJECTED: 'bad', ISSUED: 'good', APPROVED: 'good', ACCEPTED: 'good', DECLINED: 'bad', PENDING: 'info',
}

export function StatusBadge({ status }) {
  return <span className={`badge ${TONE[status] || 'info'}`}>{label(status)}</span>
}

// Private files need the Bearer token, so fetch as a blob and open it in a new tab.
export async function openFile(url) {
  const { data } = await api.get(url, { responseType: 'blob' })
  window.open(URL.createObjectURL(data), '_blank')
}

export const STAGES = ['APPLIED', 'SHORTLISTED', 'INTERVIEW_SCHEDULED', 'INTERVIEWED', 'SELECTED']

export function Tracker({ status }) {
  if (status === 'REJECTED') return <div className="tracker"><span className="step rejected">Rejected</span></div>
  const at = STAGES.indexOf(status)
  return (
    <ol className="tracker">
      {STAGES.map((s, i) => (
        <li key={s} className={`step ${i < at ? 'done' : i === at ? 'current' : ''}`}>{label(s)}</li>
      ))}
    </ol>
  )
}

export function Timeline({ events }) {
  if (!events?.length) return null
  return (
    <ol className="timeline">
      {events.map((e, i) => (
        <li key={i}>
          <b>{label(e.to_status)}</b> <span className="muted">· {fmtDateTime(e.created_at)} · {label(e.actor)}{e.note && ` · ${e.note}`}</span>
        </li>
      ))}
    </ol>
  )
}
