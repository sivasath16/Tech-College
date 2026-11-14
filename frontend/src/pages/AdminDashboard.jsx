import { useCallback, useEffect, useState } from 'react'
import api from '../api'
import AnnouncementsPanel from '../components/admin/AnnouncementsPanel'
import ApplicationsPanel from '../components/admin/ApplicationsPanel'
import DrivesPanel from '../components/admin/DrivesPanel'
import JobsPanel from '../components/admin/JobsPanel'
import OverviewPanel from '../components/admin/OverviewPanel'
import RecruitersPanel from '../components/admin/RecruitersPanel'
import StudentsPanel from '../components/admin/StudentsPanel'

const NAV = [
  ['overview', '📊', 'Overview'], ['students', '🎓', 'Students'], ['recruiters', '🏢', 'Recruiters'],
  ['jobs', '📝', 'Job Verification'], ['drives', '📅', 'Placement Drives'],
  ['announcements', '📣', 'Announcements'], ['applications', '📋', 'Applications'],
]

export default function AdminDashboard() {
  const [view, setView] = useState('overview')
  const [summary, setSummary] = useState(null)
  const loadSummary = useCallback(() => { api.get('/admin/summary').then((r) => setSummary(r.data)).catch(() => {}) }, [])
  useEffect(() => { loadSummary() }, [loadSummary])
  const badge = { recruiters: summary?.recruiters_pending, jobs: summary?.jobs_pending }

  return (
    <div className="admin">
      <aside className="sidenav">
        <h3>Placement Cell</h3>
        {NAV.map(([id, icon, text]) => (
          <button key={id} className={view === id ? 'active' : ''} onClick={() => setView(id)}>
            <span>{icon} {text}</span>{badge[id] > 0 && <b className="pill">{badge[id]}</b>}
          </button>
        ))}
      </aside>
      <section className="adminmain">
        <h2>{NAV.find((n) => n[0] === view)[2]}</h2>
        {view === 'overview' && <OverviewPanel summary={summary} go={setView} />}
        {view === 'students' && <StudentsPanel onChange={loadSummary} />}
        {view === 'recruiters' && <RecruitersPanel onChange={loadSummary} />}
        {view === 'jobs' && <JobsPanel onChange={loadSummary} />}
        {view === 'drives' && <DrivesPanel onChange={loadSummary} />}
        {view === 'announcements' && <AnnouncementsPanel />}
        {view === 'applications' && <ApplicationsPanel onChange={loadSummary} />}
      </section>
    </div>
  )
}
