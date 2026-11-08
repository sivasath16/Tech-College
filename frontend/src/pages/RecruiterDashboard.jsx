import { useCallback, useEffect, useState } from 'react'
import api, { API_URL } from '../api'
import { useAuth } from '../context/AuthContext'
import ApplicationsPanel from '../components/recruiter/ApplicationsPanel'
import CandidatesPanel from '../components/recruiter/CandidatesPanel'
import JobsPanel from '../components/recruiter/JobsPanel'
import ProfilePanel from '../components/recruiter/ProfilePanel'

const TABS = [
  ['overview', 'Overview'], ['profile', 'Company Profile'], ['jobs', 'Job Postings'],
  ['candidates', 'Find Candidates'], ['applications', 'Applications'],
]

export default function RecruiterDashboard() {
  const { user } = useAuth()
  const r = user.recruiter
  const [tab, setTab] = useState('overview')
  const [summary, setSummary] = useState(null)
  const [reviewJob, setReviewJob] = useState('')

  const loadSummary = useCallback(() => { api.get('/recruiter/summary').then((x) => setSummary(x.data)).catch(() => {}) }, [])
  useEffect(() => { loadSummary() }, [loadSummary])

  const review = (jobId) => { setReviewJob(String(jobId)); setTab('applications') }
  const stat = (label, value) => <div className="card stat"><span className="muted">{label}</span><b>{value ?? '—'}</b></div>

  return (
    <div className="stack">
      <div className="row">
        {r.logo_path && <img className="logo" src={`${API_URL}/media/${r.logo_path}`} alt={`${r.company_name} logo`} />}
        <div>
          <h2>{r.company_name}</h2>
          <span className="badge approved">{r.verification_status}</span>
        </div>
      </div>
      <div className="tabs wrap">
        {TABS.map(([id, text]) => (
          <button key={id} className={`tab ${tab === id ? 'active' : ''}`} onClick={() => { if (id !== 'applications') setReviewJob(''); setTab(id) }}>{text}</button>
        ))}
      </div>
      {tab === 'overview' && (
        <>
          <div className="grid3">
            {stat('Open postings', summary?.active_jobs)}
            {stat('Total applicants', summary?.applicants)}
            {stat('Shortlisted', summary?.shortlisted)}
            {stat('Upcoming interviews', summary?.interviews_upcoming)}
            {stat('Selected', summary?.selected)}
            {stat('All postings', summary?.total_jobs)}
          </div>
          <div className="card">
            <h3>About the company</h3>
            <p>{r.company_profile}</p>
            <dl className="dl">
              <dt>Contact person</dt><dd>{r.contact_person}</dd>
              <dt>Email</dt><dd>{user.email}</dd>
              <dt>Phone</dt><dd>{r.phone}</dd>
            </dl>
          </div>
        </>
      )}
      {tab === 'profile' && <ProfilePanel />}
      {tab === 'jobs' && <JobsPanel onChange={loadSummary} onReview={review} />}
      {tab === 'candidates' && <CandidatesPanel />}
      {tab === 'applications' && <ApplicationsPanel jobId={reviewJob} onChange={loadSummary} />}
    </div>
  )
}
