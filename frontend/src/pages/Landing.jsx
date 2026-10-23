import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'

export default function Landing() {
  const [items, setItems] = useState([])
  useEffect(() => { api.get('/announcements').then((r) => setItems(r.data)).catch(() => {}) }, [])

  return (
    <>
      <section className="hero">
        <h1>Your campus placements, in one place.</h1>
        <p>
          A single portal where students build their academic profile and apply for opportunities, recruiters post
          jobs and run campus drives, and the placement cell keeps the whole process on track.
        </p>
        <div className="row">
          <Link className="btn" to="/register/student">I'm a Student</Link>
          <Link className="btn outline" to="/register/recruiter">I'm a Recruiter</Link>
          <Link className="btn ghost" to="/login">Admin / Login</Link>
        </div>
      </section>

      <section className="grid3">
        <div className="card"><h3>Students</h3><p>Build your profile, upload your resume and track every application.</p></div>
        <div className="card"><h3>Recruiters</h3><p>Post roles, filter candidates and schedule interviews and drives.</p></div>
        <div className="card"><h3>Placement Cell</h3><p>Verify recruiters, publish drives and generate placement reports.</p></div>
      </section>

      <section className="announcements">
        <h2>Announcements &amp; Latest Drives</h2>
        {items.length === 0 && <p className="muted">No announcements yet.</p>}
        {items.map((a) => (
          <article key={a.id} className="card">
            <h3>{a.title}</h3>
            <p>{a.body}</p>
            <small className="muted">{new Date(a.created_at).toLocaleDateString()}</small>
          </article>
        ))}
      </section>
    </>
  )
}
