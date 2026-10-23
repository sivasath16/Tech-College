import { API_URL } from '../api'
import { useAuth } from '../context/AuthContext'

export default function RecruiterDashboard() {
  const { user } = useAuth()
  const r = user.recruiter
  return (
    <div className="stack">
      <div className="row">
        {r.logo_path && <img className="logo" src={`${API_URL}/media/${r.logo_path}`} alt={`${r.company_name} logo`} />}
        <div>
          <h2>{r.company_name}</h2>
          <span className="badge approved">{r.verification_status}</span>
        </div>
      </div>
      <div className="card">
        <h3>Company profile</h3>
        <p>{r.company_profile}</p>
        <dl className="dl">
          <dt>Contact person</dt><dd>{r.contact_person}</dd>
          <dt>Email</dt><dd>{user.email}</dd>
          <dt>Phone</dt><dd>{r.phone}</dd>
        </dl>
      </div>
      <p className="muted">Job posting, candidate search and interview scheduling arrive in the next phase.</p>
    </div>
  )
}
