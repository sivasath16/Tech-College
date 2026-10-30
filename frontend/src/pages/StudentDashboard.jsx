import { useCallback, useEffect, useState } from 'react'
import api from '../api'
import { useAuth } from '../context/AuthContext'
import ApplicationsPanel from '../components/student/ApplicationsPanel'
import DocumentsPanel from '../components/student/DocumentsPanel'
import JobsPanel from '../components/student/JobsPanel'
import ProfilePanel from '../components/student/ProfilePanel'
import UpdatesPanel from '../components/student/UpdatesPanel'

const TABS = [
  ['overview', 'Overview'], ['profile', 'Profile'], ['documents', 'Documents'],
  ['jobs', 'Jobs & Internships'], ['applications', 'My Applications'], ['updates', 'Drives & Updates'],
]

function Overview({ user, summary }) {
  const s = user.student
  return (
    <>
      <div className="grid3">
        <div className="card stat"><span className="muted">Placement status</span><b className={s.placement_status === 'PLACED' ? 'good' : ''}>{s.placement_status.replace('_', ' ')}</b></div>
        <div className="card stat"><span className="muted">Applications</span><b>{summary?.applications ?? '—'}</b></div>
        <div className="card stat"><span className="muted">Shortlisted</span><b>{summary?.shortlisted ?? '—'}</b></div>
        <div className="card stat"><span className="muted">Upcoming interviews</span><b>{summary?.interviews_upcoming ?? '—'}</b></div>
        <div className="card stat"><span className="muted">Offers</span><b>{summary?.offers ?? '—'}</b></div>
        <div className="card stat"><span className="muted">Degree CGPA</span><b>{s.degree_cgpa}</b></div>
      </div>
      <div className="card">
        <h3>Profile overview</h3>
        <dl className="dl">
          <dt>College ID</dt><dd>{s.college_id}</dd>
          <dt>Department</dt><dd>{s.department}</dd>
          <dt>Email</dt><dd>{user.email}</dd>
          <dt>Mobile</dt><dd>{s.mobile} {s.is_verified ? '✔ verified' : '(not verified)'}</dd>
          <dt>10th / 12th</dt><dd>{s.tenth_percent}% / {s.twelfth_percent}%</dd>
          <dt>Skills</dt><dd>{s.skills.length ? s.skills.join(', ') : '—'}</dd>
          <dt>Certifications</dt><dd>{s.certifications || '—'}</dd>
        </dl>
      </div>
    </>
  )
}

export default function StudentDashboard() {
  const { user } = useAuth()
  const [tab, setTab] = useState('overview')
  const [summary, setSummary] = useState(null)

  const loadSummary = useCallback(() => {
    api.get('/student/summary').then((r) => setSummary(r.data)).catch(() => {})
  }, [])
  useEffect(() => { loadSummary() }, [loadSummary])

  return (
    <div className="stack">
      <div className="row between">
        <h2>Welcome, {user.student.full_name}</h2>
        {summary && (
          <div className="completion" title="Add skills, a resume and a certificate to reach 100%">
            Profile {summary.profile_completion}% complete
            <div className="bar"><span style={{ width: `${summary.profile_completion}%` }} /></div>
          </div>
        )}
      </div>
      <div className="tabs wrap">
        {TABS.map(([id, text]) => (
          <button key={id} className={`tab ${tab === id ? 'active' : ''}`} onClick={() => setTab(id)}>{text}</button>
        ))}
      </div>
      {tab === 'overview' && <Overview user={user} summary={summary} />}
      {tab === 'profile' && <ProfilePanel />}
      {tab === 'documents' && <DocumentsPanel onChange={loadSummary} />}
      {tab === 'jobs' && <JobsPanel onApplied={loadSummary} />}
      {tab === 'applications' && <ApplicationsPanel />}
      {tab === 'updates' && <UpdatesPanel />}
    </div>
  )
}
