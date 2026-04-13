import { useRef, useState } from 'react'
import { api } from '../api'

const IconCloudUpload = () => (
  <svg className="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="16 16 12 12 8 16" />
    <line x1="12" y1="12" x2="12" y2="21" />
    <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
  </svg>
)

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
        className={`upload-box${drag ? ' drag' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault(); setDrag(false)
          handle(e.dataTransfer.files?.[0])
        }}
        onClick={() => !busy && inputRef.current?.click()}
      >
        <IconCloudUpload />
        <div className="upload-title">
          {busy ? 'Uploading…' : 'Drop your file here'}
        </div>
        <div className="upload-hint">
          Supports FreeStyle Libre CSV, generic CSV, and JSON — or click to browse
        </div>
        <button disabled={busy} onClick={(e) => { e.stopPropagation(); inputRef.current?.click() }}>
          {busy ? 'Uploading…' : 'Choose file'}
        </button>
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
