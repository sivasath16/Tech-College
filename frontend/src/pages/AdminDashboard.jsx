import { useCallback, useEffect, useState } from 'react'
import api, { API_URL, errorMessage } from '../api'

const FILTERS = ['PENDING', 'APPROVED', 'REJECTED']

export default function AdminDashboard() {
  const [tab, setTab] = useState('PENDING')
  const [recruiters, setRecruiters] = useState([])
  const [students, setStudents] = useState([])
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const [r, s] = await Promise.all([api.get('/admin/recruiters'), api.get('/admin/students')])
      setRecruiters(r.data)
      setStudents(s.data)
    } catch (err) { setError(errorMessage(err)) }
  }, [])
  useEffect(() => { load() }, [load])

  const decide = async (id, action) => {
    setError('')
    try {
      if (action === 'reject') {
        const reason = window.prompt('Reason for rejection?')
        if (!reason) return
        await api.post(`/admin/recruiters/${id}/reject`, { reason })
      } else {
        await api.post(`/admin/recruiters/${id}/approve`)
      }
      load()
    } catch (err) { setError(errorMessage(err)) }
  }

  const shown = recruiters.filter((r) => r.verification_status === tab)

  return (
    <div className="stack">
      <h2>Placement Cell — Admin</h2>
      <div className="grid3">
        <div className="card stat"><span className="muted">Pending recruiters</span><b>{recruiters.filter((r) => r.verification_status === 'PENDING').length}</b></div>
        <div className="card stat"><span className="muted">Approved recruiters</span><b>{recruiters.filter((r) => r.verification_status === 'APPROVED').length}</b></div>
        <div className="card stat"><span className="muted">Registered students</span><b>{students.length}</b></div>
      </div>
      {error && <div className="alert error">{error}</div>}

      <div className="card">
        <h3>Recruiter verification</h3>
        <div className="tabs">
          {FILTERS.map((f) => <button key={f} className={tab === f ? 'tab active' : 'tab'} onClick={() => setTab(f)}>{f}</button>)}
        </div>
        {shown.length === 0 && <p className="muted">No {tab.toLowerCase()} recruiters.</p>}
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
                <button className="btn small" onClick={() => decide(r.id, 'approve')}>Approve</button>
                <button className="btn small danger" onClick={() => decide(r.id, 'reject')}>Reject</button>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="card">
        <h3>Student database</h3>
        {students.length === 0 ? <p className="muted">No students registered yet.</p> : (
          <table>
            <thead><tr><th>College ID</th><th>Name</th><th>Department</th><th>CGPA</th><th>Email</th><th>Status</th></tr></thead>
            <tbody>
              {students.map((s) => (
                <tr key={s.id}><td>{s.college_id}</td><td>{s.full_name}</td><td>{s.department}</td><td>{s.degree_cgpa}</td><td>{s.email}</td><td>{s.placement_status.replace('_', ' ')}</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
