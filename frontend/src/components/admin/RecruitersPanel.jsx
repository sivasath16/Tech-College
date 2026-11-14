import { useCallback, useEffect, useState } from 'react'
import api, { API_URL, errorMessage } from '../../api'

const FILTERS = ['PENDING', 'APPROVED', 'REJECTED']

export default function RecruitersPanel({ onChange }) {
  const [tab, setTab] = useState('PENDING')
  const [rows, setRows] = useState(null)
  const [msg, setMsg] = useState(null)
  const load = useCallback(async () => {
    try { setRows((await api.get('/admin/recruiters')).data) } catch (e) { setMsg({ ok: false, text: errorMessage(e) }) }
  }, [])
  useEffect(() => { load() }, [load])

  const decide = async (r, action) => {
    setMsg(null)
    try {
      if (action === 'reject') {
        const reason = window.prompt('Reason for rejection?')
        if (!reason) return
        await api.post(`/admin/recruiters/${r.id}/reject`, { reason })
      } else await api.post(`/admin/recruiters/${r.id}/approve`)
      setMsg({ ok: true, text: `${r.company_name} ${action === 'approve' ? 'approved' : 'rejected'}` })
      load(); onChange()
    } catch (e) { setMsg({ ok: false, text: errorMessage(e) }) }
  }
  const shown = (rows || []).filter((r) => r.verification_status === tab)
  return (
    <div className="card">
      <h3>Recruiter verification</h3>
      <div className="tabs">{FILTERS.map((f) => <button key={f} className={`tab ${tab === f ? 'active' : ''}`} onClick={() => setTab(f)}>{f} ({(rows || []).filter((r) => r.verification_status === f).length})</button>)}</div>
      {msg && <div className={`alert ${msg.ok ? 'ok' : 'error'}`}>{msg.text}</div>}
      {rows && shown.length === 0 && <p className="muted">No {tab.toLowerCase()} recruiters.</p>}
      {shown.map((r) => (
        <div key={r.id} className="item">
          {r.logo_path && <img className="logo small" src={`${API_URL}/media/${r.logo_path}`} alt="" />}
          <div className="grow">
            <b>{r.company_name}</b> <span className="muted">· {r.contact_person} · {r.email} · {r.phone}</span>
            <p>{r.company_profile}</p>
            {r.rejection_reason && <small className="muted">Rejected: {r.rejection_reason}</small>}
          </div>
          {tab === 'PENDING' && (
            <div className="row">
              <button className="btn small" onClick={() => decide(r, 'approve')}>Approve</button>
              <button className="btn small danger" onClick={() => decide(r, 'reject')}>Reject</button>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
