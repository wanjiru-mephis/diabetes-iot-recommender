import { useRef, useState } from 'react'
import { api } from '../api'

export default function UploadForm({ onUploaded }) {
  const inputRef = useRef(null)
  const [drag, setDrag] = useState(false)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)
  const [err, setErr] = useState(null)

  const handle = async (file) => {
    if (!file) return
    setBusy(true); setMsg(null); setErr(null)
    try {
      const result = await api.uploadFile(file)
      setMsg(`${result.message} Features recomputed: ${result.features_recomputed ? 'yes' : 'no'}.`)
      onUploaded && onUploaded(result)
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      {msg && <div className="alert success">{msg}</div>}
      {err && <div className="alert error">{err}</div>}
      <div
        className={`upload-box ${drag ? 'drag' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault(); setDrag(false)
          handle(e.dataTransfer.files?.[0])
        }}
        onClick={() => inputRef.current?.click()}
      >
        <p style={{ margin: 0, marginBottom: 12, color: '#6b7688' }}>
          Drag & drop your glucose export here, or click to browse
        </p>
        <p style={{ margin: 0, marginBottom: 16, color: '#9aa4b5', fontSize: 12 }}>
          Supports FreeStyle Libre CSV exports, generic CSV, and JSON
        </p>
        <button disabled={busy}>{busy ? 'Uploading…' : 'Choose file'}</button>
        <input
          ref={inputRef}
          className="file-input"
          type="file"
          accept=".csv,.json"
          onChange={(e) => handle(e.target.files?.[0])}
        />
      </div>
    </div>
  )
}
