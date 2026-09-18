import { useState } from 'react'
import './App.css'

const SUPPORTED_TYPES = 'JPG • PNG'

function App() {
  const [file, setFile] = useState(null)
  const [status, setStatus] = useState('idle') // idle | selected | analyzing | removing | done
  const [results, setResults] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [fieldsToRemove, setFieldsToRemove] = useState(new Set()) // ← Tracks fields that will be REMOVED

  const selectFile = (selected) => {
    if (!selected) return
    setFile(selected)
    setStatus('selected')
    setResults(null)
    setFieldsToRemove(new Set())
  }

  const handleFileChange = (e) => selectFile(e.target.files[0])

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    selectFile(e.dataTransfer.files[0])
  }

  const handleRemove = () => {
    setFile(null)
    setStatus('idle')
    setResults(null)
    setFieldsToRemove(new Set())
  }

  const handleScrub = async () => {
    if (!file) return

    setStatus('analyzing')
    const formData = new FormData()
    formData.append('file', file)

    try {
      const analyzingDelay = new Promise((r) => setTimeout(r, 500))
      const requestPromise = fetch('http://127.0.0.1:5000/scrub', {
        method: 'POST',
        body: formData,
      })

      await analyzingDelay
      setStatus('removing')

      const res = await requestPromise
      const data = await res.json()

      setResults(data)
      
      // ← NEW: By default, ALL fields are checked for removal
      const allFieldKeys = new Set(data.fields.map(f => f.key))
      setFieldsToRemove(allFieldKeys)
      
      setStatus('done')
    } catch (err) {
      console.error(err)
      setStatus('selected')
    }
  }

  const handleDownload = async () => {
    if (!file || !results) return
    
    // ← NEW: Calculate which fields to KEEP (inverse of fieldsToRemove)
    const allFieldKeys = new Set(results.fields.map(f => f.key))
    const fieldsToKeep = [...allFieldKeys].filter(key => !fieldsToRemove.has(key))
    
    const formData = new FormData()
    formData.append('file', file)
    formData.append('keep', JSON.stringify(fieldsToKeep))

    const res = await fetch('http://127.0.0.1:5000/download', {
      method: 'POST',
      body: formData,
    })
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'cleaned_' + file.name
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleReset = () => {
    setFile(null)
    setResults(null)
    setStatus('idle')
    setFieldsToRemove(new Set())
  }

  // ← NEW: Toggle field removal (checked = will be removed)
  const toggleFieldRemoval = (key) => {
    setFieldsToRemove(prev => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key) // Uncheck = will be KEPT
      } else {
        next.add(key) // Check = will be REMOVED
      }
      return next
    })
  }

  const formatSize = (bytes) => {
    const mb = bytes / (1024 * 1024)
    return mb < 0.01 ? `${(bytes / 1024).toFixed(1)} KB` : `${mb.toFixed(1)} MB`
  }

  const extLabel = (f) => (f.name.split('.').pop() || '').toUpperCase()

  const isProcessing = status === 'analyzing' || status === 'removing'
  const isResultsScreen = status === 'done' && results

  // ← NEW: Calculate how many will be kept vs removed
  const fieldsToKeepCount = results ? results.fields.length - fieldsToRemove.size : 0

  return (
    <div className="page">
      <div className="topbar">
        <div className="brand">
          <span className="brand-dot" />
          DASCRU
        </div>
        <div className="privacy-chip">
          <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="5" y="11" width="14" height="9" rx="2" />
            <path d="M8 11V7a4 4 0 0 1 8 0v4" />
          </svg>
          <span>Privacy protected</span>
        </div>
      </div>

      {!isResultsScreen && (
        <>
          <div className="hero">
            <h1 className="hero-title">Metadata Scrubber</h1>
            <p className="hero-sub">Remove hidden information before you share.</p>
            <p className="hero-text">Protect your privacy by removing sensitive metadata from your files.</p>
          </div>

          <div className="card">
            {status === 'idle' && (
              <div
                className={`drop-zone${dragging ? ' dragging' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
              >
                <div className="drop-icon">
                  <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 3v12m0-12 4 4m-4-4-4 4M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
                  </svg>
                </div>
                <p className="drop-title">Drop your file here</p>
                <p className="drop-sub">
                  or{' '}
                  <label htmlFor="fileInput" className="browse-link">browse files</label>
                </p>
                <input
                  type="file"
                  accept="image/*"
                  id="fileInput"
                  style={{ display: 'none' }}
                  onChange={handleFileChange}
                />
                <p className="filetypes">{SUPPORTED_TYPES}</p>
              </div>
            )}

            {status === 'selected' && (
              <div className="file-row">
                <div className="file-info">
                  <div className="file-icon">{extLabel(file)}</div>
                  <div>
                    <p className="file-name">{file.name}</p>
                    <p className="file-meta">{extLabel(file)} · {formatSize(file.size)}</p>
                  </div>
                </div>
                <button className="remove-btn" onClick={handleRemove}>Remove</button>
              </div>
            )}

            {isProcessing && (
              <div className="processing">
                <p className="processing-title">
                  {status === 'analyzing' ? 'Analyzing file...' : 'Removing sensitive metadata...'}
                </p>
                <p className="processing-sub">This only takes a moment.</p>
                <div className="bar-track"><div className="bar-fill" /></div>
              </div>
            )}
          </div>

          <button
            className="primary-btn"
            onClick={handleScrub}
            disabled={!file || isProcessing}
          >
            {isProcessing ? 'Scrubbing...' : 'Scrub file'}
          </button>
        </>
      )}

      {isResultsScreen && (
        <>
          <div className="success-block">
            <div className="success-icon">
              <svg viewBox="0 0 24 24" fill="none" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 6 9 17l-5-5" />
              </svg>
            </div>
            <h1 className="success-title">File scanned successfully</h1>
            <p className="success-sub">
              {results.fields.length} metadata field{results.fields.length !== 1 ? 's' : ''} detected.
              {fieldsToRemove.size} will be removed, {fieldsToKeepCount} preserved.
            </p>
          </div>

          <div className="card">
            <div className="results-header">
              <p className="results-title">Select fields to remove</p>
              <span className="results-count">{fieldsToRemove.size} of {results.fields.length} selected</span>
            </div>

            {results.fields.length === 0 ? (
              <div className="empty-fields">No metadata was found in this file.</div>
            ) : (
              <div className="field-list">
                {results.fields.map((f) => (
                  <label className="field-item" key={f.key}>
                    {/* ✅ Checked = will be REMOVED */}
                    <input
                      type="checkbox"
                      className="field-checkbox"
                      checked={fieldsToRemove.has(f.key)}
                      onChange={() => toggleFieldRemoval(f.key)}
                    />
                    <div className="field-content">
                      <div>
                        <p className="field-label">{f.label}</p>
                        <p className="field-message">{f.message}</p>
                      </div>
                      <span className={`risk-badge risk-${f.risk}`}>{f.risk}</span>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>

          <div className="actions">
            <button className="primary-btn" onClick={handleDownload}>
              ↓ Download cleaned file
              {fieldsToKeepCount > 0 && ` (keeping ${fieldsToKeepCount})`}
            </button>
            <button className="scrub-another" onClick={handleReset}>
              Scrub another file
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export default App