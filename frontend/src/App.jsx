import { useState } from 'react'
import './App.css'

const SUPPORTED_TYPES = 'JPG • PNG'

const PRESET_META = {
  legal: {
    label: 'Legal (Remove Everything)',
    blurb: 'Strips all detected metadata fields for maximum privacy.',
  },
  social: {
    label: 'Social Media',
    blurb: 'Strips GPS location & camera model. Keeps artist, timestamps, and software.',
  },
  resume: {
    label: 'Resume / Portfolio',
    blurb: 'Strips GPS location only. Keeps camera specs, software, timestamps, and artist.',
  },
  custom: {
    label: 'Custom Selection',
    blurb: 'Custom configuration set manually.',
  },
}

function categorizeField(field) {
  if (!field) return 'other'

  const key = String(field.key || '').toLowerCase()
  const label = String(field.label || '').toLowerCase()
  const combined = `${key} ${label}`

  if (
    combined.includes('time') ||
    combined.includes('date') ||
    combined.includes('timestamp') ||
    combined.includes('created') ||
    combined.includes('modified')
  ) {
    return 'timestamp'
  }
  if (
    combined.includes('gps') ||
    combined.includes('latitude') ||
    combined.includes('longitude') ||
    combined.includes('location') ||
    combined.includes('geo') ||
    combined.includes('altitude')
  ) {
    return 'location'
  }
  if (
    combined.includes('artist') ||
    combined.includes('author') ||
    combined.includes('creator') ||
    combined.includes('copyright') ||
    combined.includes('credit') ||
    combined.includes('by-line') ||
    combined.includes('owner')
  ) {
    return 'author'
  }

  if (
    combined.includes('software') ||
    combined.includes('program') ||
    combined.includes('editor') ||
    combined.includes('processing') ||
    combined.includes('history')
  ) {
    return 'software'
  }

  if (
    combined.includes('camera') ||
    combined.includes('make') ||
    combined.includes('model') ||
    combined.includes('lens') ||
    combined.includes('manufacturer') ||
    combined.includes('device') ||
    combined.includes('serial')
  ) {
    return 'device'
  }

  return 'other'
}

function getFieldsToRemoveForPreset(presetType, fieldsList) {
  const toRemoveSet = new Set()
  if (!Array.isArray(fieldsList)) return toRemoveSet

  fieldsList.forEach((field) => {
    if (!field || !field.key) return

    const category = categorizeField(field)
    let isMarkedForRemoval = false

    if (presetType === 'legal') {
      isMarkedForRemoval = true
    } else if (presetType === 'social') {
      isMarkedForRemoval = category === 'location' || category === 'device'
    } else if (presetType === 'resume') {
      isMarkedForRemoval = category === 'location'
    }

    if (isMarkedForRemoval) {
      toRemoveSet.add(field.key)
    }
  })

  return toRemoveSet
}

function App() {
  const [file, setFile] = useState(null)

  const [status, setStatus] = useState('idle') // idle | selected | analyzing | removing | done
  const [results, setResults] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [fieldsToRemove, setFieldsToRemove] = useState(new Set())
  const [preset, setPreset] = useState('legal')

  const [stats, setStats] = useState({
    filesProcessed: 0,
    metadataDetected: 0,
    metadataRemoved: 0,
  })

  const selectFile = (selected) => {
    if (!selected) return
    setFile(selected)
    setStatus('selected')
    setResults(null)
    setFieldsToRemove(new Set())
    setPreset('legal')
  }

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      selectFile(e.target.files[0])
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      selectFile(e.dataTransfer.files[0])
    }
  }

  const handleClearFile = () => {
    setFile(null)
    setStatus('idle')
    setResults(null)
    setFieldsToRemove(new Set())
    setPreset('legal')
  }

  const handlePresetChange = (e) => {
    const newPreset = e.target.value
    setPreset(newPreset)
    if (newPreset !== 'custom') {
      const fieldsList = results?.fields || []
      setFieldsToRemove(getFieldsToRemoveForPreset(newPreset, fieldsList))
    }
  }

  const handleScrub = async () => {
    if (!file) return

    setStatus('analyzing')
    const formData = new FormData()
    formData.append('file', file)

    try {
      const analyzingDelay = new Promise((r) => setTimeout(r, 400))
      const requestPromise = fetch('http://127.0.0.1:5000/scrub', {
        method: 'POST',
        body: formData,
      })

      await analyzingDelay
      setStatus('removing')

      const res = await requestPromise
      if (!res.ok) throw new Error(`Server returned ${res.status}`)
      const data = await res.json()

      setResults(data)
      setStats((prev) => ({
        ...prev,
        filesProcessed: prev.filesProcessed + 1,
        metadataDetected: prev.metadataDetected + (data?.fields?.length || 0),
      }))

      const initialPreset = 'legal'
      setPreset(initialPreset)
      const fieldsList = data?.fields || []
      setFieldsToRemove(getFieldsToRemoveForPreset(initialPreset, fieldsList))

      setStatus('done')
    } catch (err) {
      console.error('Scrub error:', err)
      alert('Failed to scrub file. Make sure backend is running on port 5000.')
      setStatus('selected')
    }
  }

  const handleDownload = async () => {
    if (!file || !results) return

    try {
      const fieldsList = results?.fields || []
      const allFieldKeys = fieldsList.map((f) => f.key)
      const fieldsToKeep = allFieldKeys.filter((key) => !fieldsToRemove.has(key))
      setStats((prev) => ({
        ...prev,
        metadataRemoved: prev.metadataRemoved + fieldsToRemove.size,
      }))
      const formData = new FormData()
      formData.append('file', file)
      formData.append('keep', JSON.stringify(fieldsToKeep))

      const res = await fetch('http://127.0.0.1:5000/download', {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) throw new Error(`Download failed with status ${res.status}`)

      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'cleaned_' + file.name
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Download error:', err)
      alert('Failed to download cleaned file.')
    }
  }

  const handleReset = () => {
    setFile(null)
    setResults(null)
    setStatus('idle')
    setFieldsToRemove(new Set())
    setPreset('legal')
  }

  const toggleFieldRemoval = (key) => {
    setPreset('custom')
    setFieldsToRemove((prev) => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }

  const formatSize = (bytes) => {
    if (!bytes) return '0 KB'
    const mb = bytes / (1024 * 1024)
    return mb < 0.01 ? `${(bytes / 1024).toFixed(1)} KB` : `${mb.toFixed(1)} MB`
  }

  const extLabel = (f) => (f && f.name ? (f.name.split('.').pop() || '').toUpperCase() : 'FILE')

  const isProcessing = status === 'analyzing' || status === 'removing'
  const isResultsScreen = status === 'done' && results
  const fieldsList = results?.fields || []
  const totalFieldsCount = fieldsList.length
  const fieldsToKeepCount = totalFieldsCount - fieldsToRemove.size

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

      <div className="main-layout">
        {!isResultsScreen && (
          <>
            <div className="dashboard">
              <div className="dashboard-header">
                <h1>Dashboard</h1>
                <p>Overview of your metadata privacy activity.</p>
              </div>

              <div className="stats-grid">
                <div className="stat-card">
                  <p className="stat-label">Files Processed</p>
                  <h2>{stats.filesProcessed}</h2>
                  <p className="stat-description">Files scrubbed successfully</p>
                </div>

                <div className="stat-card">
                  <p className="stat-label">Metadata Detected</p>
                  <h2>{stats.metadataDetected}</h2>
                  <p className="stat-description">Metadata fields found</p>
                </div>

                <div className="stat-card">
                  <p className="stat-label">Metadata Removed</p>
                  <h2>{stats.metadataRemoved}</h2>
                  <p className="stat-description">Sensitive fields removed</p>
                </div>
              </div>

              <div className="dashboard-action">
                <div>
                  <h2>Ready to protect your file?</h2>
                  <p>Remove sensitive metadata before sharing your files.</p>
                </div>

                <button
                  className="primary-btn"
                  onClick={() => document.querySelector('.drop-card')?.scrollIntoView({ behavior: 'smooth' })}
                >
                  Scrub a file
                </button>
              </div>

              <div className="features-section">
                <h2>What DASCRU protects</h2>

                <div className="features-grid">
                  <div className="feature-card">
                    <h3>Location</h3>
                    <p>Remove GPS coordinates and location information.</p>
                  </div>

                  <div className="feature-card">
                    <h3>Device Information</h3>
                    <p>Remove camera and device details from your files.</p>
                  </div>

                  <div className="feature-card">
                    <h3>Timestamps</h3>
                    <p>Control timestamps and other hidden file information.</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="scrubber-section">
              <div className="hero">
                <h1 className="hero-title">Metadata Scrubber</h1>
                <p className="hero-sub">Remove hidden information before you share.</p>
                <p className="hero-text">Protect your privacy by removing sensitive metadata from your files.</p>
              </div>

              <div className="card">
                {status === 'idle' && (
                  <div
                    className={`drop-zone${dragging ? ' dragging' : ''}`}
                    onDragOver={(e) => {
                      e.preventDefault()
                      setDragging(true)
                    }}
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
                      or <label htmlFor="fileInput" className="browse-link">browse files</label>
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

                {status === 'selected' && file && (
                  <div className="file-row">
                    <div className="file-info">
                      <div className="file-icon">{extLabel(file)}</div>
                      <div>
                        <p className="file-name">{file.name}</p>
                        <p className="file-meta">
                          {extLabel(file)} · {formatSize(file.size)}
                        </p>
                      </div>
                    </div>
                    <button className="remove-btn" onClick={handleClearFile}>
                      Remove
                    </button>
                  </div>
                )}

                {isProcessing && (
                  <div className="processing">
                    <p className="processing-title">
                      {status === 'analyzing' ? 'Analyzing file...' : 'Removing sensitive metadata...'}
                    </p>
                    <p className="processing-sub">This only takes a moment.</p>
                    <div className="bar-track">
                      <div className="bar-fill" />
                    </div>
                  </div>
                )}
              </div>

              <button className="primary-btn" onClick={handleScrub} disabled={!file || isProcessing}>
                {isProcessing ? 'Scrubbing...' : 'Scrub file'}
              </button>
            </div>
          </>
        )}

        {isResultsScreen && (
          <div className="scrubber-section">
            <div className="success-block">
              <div className="success-icon">
                <svg viewBox="0 0 24 24" fill="none" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 6 9 17l-5-5" />
                </svg>
              </div>
              <h1 className="success-title">File scanned successfully</h1>
              <p className="success-sub">
                {totalFieldsCount} metadata field{totalFieldsCount !== 1 ? 's' : ''} detected.{' '}
                {fieldsToRemove.size} will be removed, {fieldsToKeepCount} preserved.
              </p>
            </div>

            <div className="card">
              <div className="preset-bar">
                <div className="preset-text">
                  <label htmlFor="preset" className="preset-label">
                    Category Preset
                  </label>
                  <p className="preset-blurb">{PRESET_META[preset]?.blurb}</p>
                </div>
                <select
                  id="preset"
                  className="preset-select"
                  value={preset}
                  onChange={handlePresetChange}
                >
                  <option value="legal">{PRESET_META.legal.label}</option>
                  <option value="social">{PRESET_META.social.label}</option>
                  <option value="resume">{PRESET_META.resume.label}</option>
                  <option value="custom">{PRESET_META.custom.label}</option>
                </select>
              </div>

              <div className="results-header">
                <p className="results-title">Select fields to remove</p>
                <span className="results-count">
                  {fieldsToRemove.size} of {totalFieldsCount} selected
                </span>
              </div>

              {totalFieldsCount > 0 && (
                <div className="field-header-row">
                  <span></span>
                  <span>Field</span>
                  <span>What it reveals</span>
                  <span>Risk</span>
                </div>
              )}

              {totalFieldsCount === 0 ? (
                <div className="empty-fields">No metadata was found in this file.</div>
              ) : (
                <div className="field-list">
                  {fieldsList.map((f) => {
                    const isWillBeRemoved = fieldsToRemove.has(f.key)
                    return (
                      <label className={`field-item${!isWillBeRemoved ? ' is-kept' : ''}`} key={f.key}>
                        <input
                          type="checkbox"
                          className="field-checkbox"
                          checked={isWillBeRemoved}
                          onChange={() => toggleFieldRemoval(f.key)}
                        />

                        <div className="col-name">
                          <p className="field-label">
                            {f.label}
                            {!isWillBeRemoved && <span className="kept-tag">preserved</span>}
                          </p>
                          {f.value && <p className="field-value">{f.value}</p>}
                        </div>

                        <div className="col-message">
                          {f.message || '—'}
                        </div>

                        <div className="col-risk">
                          <span className={`risk-badge risk-${(f.risk || 'low').toLowerCase()}`}>
                            {f.risk || 'LOW'}
                          </span>
                        </div>
                      </label>
                    )
                  })}
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
          </div>
        )}
      </div>
    </div>
  )
}

export default App