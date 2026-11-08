import { useState } from 'react'
import api, { errorMessage } from '../../api'
import Field from '../Field'

const list = (s) => s.split(',').map((x) => x.trim()).filter(Boolean)
const today = () => new Date().toISOString().slice(0, 10)

export default function JobForm({ job, onSaved, onCancel }) {
  const [form, setForm] = useState(job ? {
    ...job, salary: job.salary || '', required_skills: job.required_skills.join(', '),
    eligible_departments: job.eligible_departments.join(', '),
  } : {
    title: '', job_type: 'JOB', description: '', location: '', salary: '', required_skills: '',
    min_cgpa: 0, eligible_departments: '', deadline: '',
  })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault(); setError(''); setBusy(true)
    const body = {
      title: form.title, job_type: form.job_type, description: form.description, location: form.location,
      salary: form.salary || null, required_skills: list(form.required_skills), min_cgpa: Number(form.min_cgpa),
      eligible_departments: list(form.eligible_departments), deadline: form.deadline,
    }
    try {
      const { data } = job ? await api.put(`/recruiter/jobs/${job.id}`, body) : await api.post('/recruiter/jobs', body)
      onSaved(data)
    } catch (err) { setError(errorMessage(err)) } finally { setBusy(false) }
  }

  return (
    <form className="card form wide" onSubmit={submit}>
      <h3>{job ? `Edit: ${job.title}` : 'Post a new job or internship'}</h3>
      {error && <div className="alert error">{error}</div>}
      <div className="cols">
        <Field label="Role / title"><input required minLength={3} value={form.title} onChange={set('title')} /></Field>
        <Field label="Type">
          <select value={form.job_type} onChange={set('job_type')}><option value="JOB">Job</option><option value="INTERNSHIP">Internship</option></select>
        </Field>
        <Field label="Location"><input required value={form.location} onChange={set('location')} /></Field>
        <Field label="Salary / stipend" hint="e.g. 8 LPA or ₹25,000 / month"><input value={form.salary} onChange={set('salary')} /></Field>
        <Field label="Minimum CGPA"><input type="number" step="0.01" min="0" max="10" required value={form.min_cgpa} onChange={set('min_cgpa')} /></Field>
        <Field label="Application deadline"><input type="date" required min={today()} value={form.deadline} onChange={set('deadline')} /></Field>
      </div>
      <Field label="Required skills" hint="Comma separated, e.g. Python, SQL"><input value={form.required_skills} onChange={set('required_skills')} /></Field>
      <Field label="Eligible departments" hint="Comma separated. Leave empty to allow every department"><input value={form.eligible_departments} onChange={set('eligible_departments')} /></Field>
      <Field label="Description"><textarea required rows={4} minLength={10} value={form.description} onChange={set('description')} /></Field>
      <div className="row">
        <button className="btn" disabled={busy}>{busy ? 'Saving…' : job ? 'Save changes' : 'Publish posting'}</button>
        <button type="button" className="btn ghost" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}
