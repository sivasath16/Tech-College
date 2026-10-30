import { useCallback, useEffect, useRef, useState } from 'react'
import api, { errorMessage } from '../../api'
import Field from '../Field'
import { fmtDate, openFile } from './format'

export default function DocumentsPanel({ onChange }) {
  const [docs, setDocs] = useState(null)
  const [msg, setMsg] = useState(null)
  const [title, setTitle] = useState('')
  const resumeInput = useRef(null)
  const certInput = useRef(null)

  const load = useCallback(async () => {
    try { setDocs((await api.get('/student/documents')).data) } catch (err) { setMsg({ ok: false, text: errorMessage(err) }) }
  }, [])
  useEffect(() => { load() }, [load])

  const run = async (action, okText) => {
    setMsg(null)
    try {
      setDocs((await action()).data)
      setMsg({ ok: true, text: okText })
      onChange?.()
    } catch (err) { setMsg({ ok: false, text: errorMessage(err) }) }
  }

  const uploadResume = () => {
    const file = resumeInput.current.files[0]
    if (!file) return
    const body = new FormData()
    body.append('file', file)
    run(() => api.post('/student/resume', body), 'Resume uploaded').finally(() => { resumeInput.current.value = '' })
  }

  const uploadCert = (e) => {
    e.preventDefault()
    const file = certInput.current.files[0]
    if (!file) return
    const body = new FormData()
    body.append('title', title)
    body.append('file', file)
    run(() => api.post('/student/certificates', body), 'Certificate uploaded').then(() => {
      setTitle(''); certInput.current.value = ''
    })
  }

  if (!docs) return <p className="muted">Loading documents…</p>
  return (
    <div className="stack">
      {msg && <div className={`alert ${msg.ok ? 'ok' : 'error'}`}>{msg.text}</div>}
      <div className="card">
        <h3>Resume</h3>
        {docs.resume_name
          ? <p>Current resume: <button className="link" onClick={() => openFile('/student/resume')}>{docs.resume_name}</button></p>
          : <p className="muted">No resume uploaded yet. You need one before you can apply to jobs.</p>}
        <div className="row">
          <input ref={resumeInput} type="file" accept=".pdf,.docx" className="file" />
          <button className="btn" type="button" onClick={uploadResume}>{docs.resume_name ? 'Replace resume' : 'Upload resume'}</button>
        </div>
        <small className="muted">PDF or DOCX, up to 5 MB.</small>
      </div>

      <div className="card">
        <h3>Certificates</h3>
        {docs.certificates.length === 0 && <p className="muted">No certificates uploaded.</p>}
        {docs.certificates.map((c) => (
          <div className="item" key={c.id}>
            <div className="grow">
              <b>{c.title}</b>
              <p className="muted">{c.original_name} · uploaded {fmtDate(c.created_at)}</p>
            </div>
            <button className="btn small outline" onClick={() => openFile(`/student/certificates/${c.id}`)}>View</button>
            <button className="btn small danger" onClick={() => run(() => api.delete(`/student/certificates/${c.id}`), 'Certificate removed')}>Delete</button>
          </div>
        ))}
        <form className="cols upload" onSubmit={uploadCert}>
          <Field label="Certificate title"><input required minLength={2} value={title} onChange={(e) => setTitle(e.target.value)} /></Field>
          <Field label="File" hint="PDF, PNG or JPEG, up to 5 MB"><input ref={certInput} required type="file" accept=".pdf,.png,.jpg,.jpeg" className="file" /></Field>
          <div className="end"><button className="btn">Upload certificate</button></div>
        </form>
      </div>
    </div>
  )
}
