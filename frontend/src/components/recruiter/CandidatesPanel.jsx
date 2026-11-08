import { useCallback, useEffect, useState } from 'react'
import api, { errorMessage } from '../../api'

export default function CandidatesPanel() {
  const [filters, setFilters] = useState({ q: '', skills: '', department: '', min_cgpa: '', eligible_for: '' })
  const [jobs, setJobs] = useState([])
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')
  const set = (k) => (e) => setFilters({ ...filters, [k]: e.target.value })

  useEffect(() => { api.get('/recruiter/jobs').then((r) => setJobs(r.data)).catch(() => {}) }, [])

  const search = useCallback(async () => {
    setError('')
    const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== ''))
    try { setRows((await api.get('/recruiter/candidates', { params })).data) } catch (err) { setError(errorMessage(err)) }
  }, [filters])
  useEffect(() => { const t = setTimeout(search, 300); return () => clearTimeout(t) }, [search])

  return (
    <div className="stack">
      <div className="card">
        <h3>Find candidates</h3>
        <div className="cols">
          <label className="field"><span>Name or college ID</span><input value={filters.q} onChange={set('q')} /></label>
          <label className="field"><span>Skills (all must match)</span><input placeholder="Python, SQL" value={filters.skills} onChange={set('skills')} /></label>
          <label className="field"><span>Department</span><input value={filters.department} onChange={set('department')} /></label>
          <label className="field"><span>Minimum CGPA</span><input type="number" step="0.1" min="0" max="10" value={filters.min_cgpa} onChange={set('min_cgpa')} /></label>
          <label className="field"><span>Eligible for my posting</span>
            <select value={filters.eligible_for} onChange={set('eligible_for')}>
              <option value="">Any</option>
              {jobs.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
            </select>
          </label>
        </div>
      </div>
      {error && <div className="alert error">{error}</div>}
      <p className="muted">{rows ? `${rows.length} candidate${rows.length === 1 ? '' : 's'} found` : 'Searching…'} · contact details are shared once a student applies to your posting.</p>
      {rows?.length > 0 && (
        <div className="card">
          <table>
            <thead><tr><th>College ID</th><th>Name</th><th>Department</th><th>CGPA</th><th>Skills</th><th>Status</th></tr></thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.id}>
                  <td>{c.college_id}</td><td>{c.full_name}</td><td>{c.department}</td><td>{c.degree_cgpa}</td>
                  <td>{c.skills.join(', ') || '—'}</td>
                  <td><span className={`badge ${c.placement_status === 'PLACED' ? 'good' : 'info'}`}>{c.placement_status === 'PLACED' ? 'Placed' : 'Not placed'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
