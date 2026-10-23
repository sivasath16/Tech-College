import { useAuth } from '../context/AuthContext'

export default function StudentDashboard() {
  const { user } = useAuth()
  const s = user.student
  return (
    <div className="stack">
      <h2>Welcome, {s.full_name}</h2>
      <div className="grid3">
        <div className="card stat"><span className="muted">Placement status</span><b className={s.placement_status === 'PLACED' ? 'good' : ''}>{s.placement_status.replace('_', ' ')}</b></div>
        <div className="card stat"><span className="muted">Degree CGPA</span><b>{s.degree_cgpa}</b></div>
        <div className="card stat"><span className="muted">Mobile</span><b>{s.is_verified ? 'Verified ✔' : 'Not verified'}</b></div>
      </div>
      <div className="card">
        <h3>Profile overview</h3>
        <dl className="dl">
          <dt>College ID</dt><dd>{s.college_id}</dd>
          <dt>Department</dt><dd>{s.department}</dd>
          <dt>Email</dt><dd>{user.email}</dd>
          <dt>10th / 12th</dt><dd>{s.tenth_percent}% / {s.twelfth_percent}%</dd>
          <dt>Skills</dt><dd>{s.skills.length ? s.skills.join(', ') : '—'}</dd>
          <dt>Certifications</dt><dd>{s.certifications || '—'}</dd>
        </dl>
      </div>
      <p className="muted">Job listings, applications and placement drives arrive in the next phase.</p>
    </div>
  )
}
