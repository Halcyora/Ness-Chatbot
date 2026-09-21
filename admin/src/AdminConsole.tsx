import React, { useState, useEffect } from 'react'

interface PageCandidate {
  url: string
  title: string
  status: 'included' | 'excluded' | 'pending'
  last_scraped?: string
}

interface AdminConsoleProps {
  apiUrl?: string
  siteId?: string
}

// Shared styles for both the login screen and the dashboard, rendered once per mounted branch
const AdminStyles: React.FC = () => (
  <style>{`
    .admin-console {
      min-height: 100vh;
      background: #f9fafb;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    .admin-container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
    }

    .admin-header {
      background: white;
      padding: 20px;
      border-bottom: 1px solid #e5e7eb;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .admin-header h1 {
      margin: 0;
      color: #1f2937;
      font-size: 24px;
    }

    .admin-header p {
      margin: 5px 0 0 0;
      color: #6b7280;
      font-size: 14px;
    }

    .logout-btn {
      padding: 10px 20px;
      background: #ef4444;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
    }

    .logout-btn:hover {
      background: #dc2626;
    }

    .auth-screen {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 45%, #3b82f6 100%);
    }

    .auth-card {
      background: white;
      padding: 40px;
      border-radius: 16px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25);
      max-width: 400px;
      width: 100%;
      text-align: center;
    }

    .auth-logo {
      width: 56px;
      height: 56px;
      margin: 0 auto 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
      border-radius: 50%;
      background: #eff6ff;
    }

    .auth-card h1 {
      margin: 0 0 8px 0;
      color: #1f2937;
      font-size: 22px;
    }

    .auth-subtitle {
      margin: 0 0 28px 0;
      color: #6b7280;
      font-size: 14px;
      line-height: 1.5;
    }

    .auth-form {
      display: flex;
      flex-direction: column;
      gap: 20px;
      text-align: left;
    }

    .auth-submit {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 12px 16px;
      font-size: 15px;
    }

    .spinner {
      width: 14px;
      height: 14px;
      border: 2px solid rgba(255, 255, 255, 0.4);
      border-top-color: #fff;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
    }

    @keyframes spin {
      to {
        transform: rotate(360deg);
      }
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .form-group label {
      font-weight: 500;
      color: #1f2937;
    }

    .input-group {
      display: flex;
      align-items: center;
      gap: 0;
      border: 1px solid #d1d5db;
      border-radius: 8px;
      overflow: hidden;
      transition: border-color 0.2s, box-shadow 0.2s;
    }

    .input-group:focus-within {
      border-color: #3b82f6;
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
    }

    .input-icon {
      padding: 0 10px;
      color: #9ca3af;
      font-size: 14px;
    }

    .input-group input {
      flex: 1;
      padding: 12px 10px 12px 0;
      border: none;
      outline: none;
      font-size: 14px;
    }

    .toggle-btn {
      padding: 10px 14px;
      background: transparent;
      border: none;
      border-left: 1px solid #e5e7eb;
      cursor: pointer;
      font-size: 16px;
    }

    .form-group small {
      color: #9ca3af;
      font-size: 12px;
    }

    .btn {
      padding: 10px 16px;
      border: none;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    }

    .btn-primary {
      background: #1e40af;
      color: white;
    }

    .btn-primary:hover:not(:disabled) {
      background: #1e3a8a;
    }

    .btn-primary:disabled {
      background: #9ca3af;
      cursor: not-allowed;
    }

    .btn-secondary {
      background: #f3f4f6;
      color: #1f2937;
      border: 1px solid #d1d5db;
    }

    .btn-secondary:hover:not(:disabled) {
      background: #e5e7eb;
    }

    .info-box {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 6px;
      padding: 15px;
      margin-top: 20px;
    }

    .info-box h3 {
      margin: 0 0 10px 0;
      color: #1e40af;
      font-size: 14px;
    }

    .info-box p {
      margin: 0;
      color: #1e40af;
      font-size: 13px;
    }

    .info-box code {
      background: white;
      padding: 2px 6px;
      border-radius: 3px;
      font-family: monospace;
    }

    .error-message {
      background: #fee2e2;
      color: #991b1b;
      padding: 12px;
      border-radius: 6px;
      margin-bottom: 20px;
      border-left: 4px solid #dc2626;
    }

    .stats-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 16px;
      margin: 20px 0;
    }

    .stat {
      background: white;
      padding: 20px;
      border-radius: 8px;
      text-align: center;
      border: 1px solid #e5e7eb;
    }

    .stat-value {
      font-size: 32px;
      font-weight: 700;
      color: #1e40af;
    }

    .stat-label {
      font-size: 12px;
      color: #6b7280;
      margin-top: 8px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .action-bar {
      display: flex;
      gap: 12px;
      margin: 20px 0;
    }

    .progress-bar {
      background: white;
      height: 30px;
      border-radius: 6px;
      overflow: hidden;
      margin: 20px 0;
      border: 1px solid #e5e7eb;
    }

    .progress-fill {
      background: linear-gradient(90deg, #1e40af, #1e3a8a);
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 12px;
      font-weight: 600;
      transition: width 0.3s;
    }

    .loading-message,
    .empty-message {
      background: white;
      padding: 40px;
      border-radius: 8px;
      text-align: center;
      color: #6b7280;
    }

    .pages-table-wrapper {
      background: white;
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid #e5e7eb;
    }

    .pages-table {
      width: 100%;
      border-collapse: collapse;
    }

    .pages-table thead {
      background: #f9fafb;
      border-bottom: 2px solid #e5e7eb;
    }

    .pages-table th {
      padding: 12px;
      text-align: left;
      font-size: 12px;
      font-weight: 600;
      color: #6b7280;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .pages-table td {
      padding: 12px;
      border-bottom: 1px solid #e5e7eb;
      font-size: 14px;
    }

    .page-row:hover {
      background: #f9fafb;
    }

    .page-row.status-excluded {
      opacity: 0.6;
    }

    .page-title {
      font-weight: 500;
      color: #1f2937;
      max-width: 300px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .page-url a {
      color: #1e40af;
      text-decoration: none;
      font-size: 13px;
      font-family: monospace;
    }

    .page-url a:hover {
      text-decoration: underline;
    }

    .page-date {
      color: #9ca3af;
      font-size: 13px;
    }

    .status-badge {
      display: inline-block;
      padding: 6px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 500;
      text-transform: capitalize;
    }

    .status-badge.status-included {
      background: #dcfce7;
      color: #166534;
    }

    .status-badge.status-excluded {
      background: #fee2e2;
      color: #991b1b;
    }

    .status-badge.status-pending {
      background: #fef3c7;
      color: #92400e;
    }

    @media (max-width: 768px) {
      .admin-header {
        flex-direction: column;
        gap: 15px;
        align-items: flex-start;
      }

      .pages-table {
        font-size: 12px;
      }

      .pages-table th,
      .pages-table td {
        padding: 8px;
      }

      .page-title {
        max-width: 150px;
      }

      .action-bar {
        flex-direction: column;
      }
    }
  `}</style>
)

const AdminConsole: React.FC<AdminConsoleProps> = ({
  apiUrl = 'http://localhost:8080',
  siteId = 'ness',
}) => {
  const [pages, setPages] = useState<PageCandidate[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // apiKey is only set once the backend has confirmed it is valid
  const [apiKey, setApiKey] = useState('')
  // keyInput tracks the (unvalidated) text typed into the login form
  const [keyInput, setKeyInput] = useState('')
  const [showApiKey, setShowApiKey] = useState(false)
  const [embeddingProgress, setEmbeddingProgress] = useState(0)
  const [selectedCount, setSelectedCount] = useState(0)

  // Try any previously-saved API key on mount, but only accept it once validated
  useEffect(() => {
    const saved = sessionStorage.getItem('admin_api_key')
    if (saved) {
      setKeyInput(saved)
      authenticate(saved)
    }
  }, [])

  // Update selected count
  useEffect(() => {
    const count = pages.filter((p) => p.status === 'included').length
    setSelectedCount(count)
  }, [pages])

  const getHeaders = () => ({
    'Content-Type': 'application/json',
    'X-Admin-Key': apiKey,
  })

  const handleApiKeySubmit = (e: React.FormEvent) => {
    e.preventDefault()
    authenticate(keyInput)
  }

  // Validates the key against the backend; only grants access on success
  const authenticate = async (key: string) => {
    if (!key) {
      setError('Please enter an API key')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${apiUrl}/admin/pages?site_id=${siteId}`, {
        headers: { 'X-Admin-Key': key },
      })

      if (response.status === 401 || response.status === 403) {
        throw new Error('Invalid API key. Check ADMIN_API_KEY in your backend .env file.')
      }
      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`)
      }

      const data = await response.json()
      setPages(data.pages || [])
      // Only now do we mark the session as authenticated
      setApiKey(key)
      sessionStorage.setItem('admin_api_key', key)
    } catch (err) {
      sessionStorage.removeItem('admin_api_key')
      setError(
        err instanceof Error
          ? err.message
          : `Failed to reach API at ${apiUrl}. Is the backend running?`
      )
    } finally {
      setLoading(false)
    }
  }

  const loadPages = async (key: string) => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${apiUrl}/admin/pages?site_id=${siteId}`, {
        headers: { 'X-Admin-Key': key },
      })

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`)
      }

      const data = await response.json()
      setPages(data.pages || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pages')
    } finally {
      setLoading(false)
    }
  }

  const togglePageStatus = async (url: string, currentStatus: string) => {
    const newStatus = currentStatus === 'included' ? 'excluded' : 'included'

    try {
      const response = await fetch(`${apiUrl}/admin/pages/${encodeURIComponent(url)}?site_id=${siteId}`, {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify({ url, status: newStatus }),
      })

      if (!response.ok) {
        throw new Error(`Failed to update page status`)
      }

      // Update local state
      setPages((prev) =>
        prev.map((p) => (p.url === url ? { ...p, status: newStatus as any } : p))
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update page')
    }
  }

  const handleSelectAll = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const newStatus = e.target.checked ? 'included' : 'excluded'
    
    // Update all pages in the database
    try {
      const updatePromises = pages.map((page) =>
        fetch(`${apiUrl}/admin/pages/${encodeURIComponent(page.url)}?site_id=${siteId}`, {
          method: 'PUT',
          headers: getHeaders(),
          body: JSON.stringify({ url: page.url, status: newStatus }),
        })
      )
      
      const responses = await Promise.all(updatePromises)
      const allOk = responses.every((r) => r.ok)
      
      if (!allOk) {
        throw new Error('Failed to update some pages')
      }
      
      // Update local state only after database updates succeed
      setPages((prev) => prev.map((p) => ({ ...p, status: newStatus as any })))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update pages')
    }
  }

  const handleRefreshPages = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${apiUrl}/admin/refresh?site_id=${siteId}`, {
        method: 'POST',
        headers: getHeaders(),
      })

      if (!response.ok) {
        throw new Error('Refresh failed')
      }

      const data = await response.json()
      alert(`Discovered ${data.discovered_count} new pages`)
      await loadPages(apiKey)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Refresh failed')
    } finally {
      setLoading(false)
    }
  }

  const handleEmbedSelected = async () => {
    if (selectedCount === 0) {
      alert('Please select at least one page to embed')
      return
    }

    if (!window.confirm(`Embed ${selectedCount} selected pages? This may take a few minutes.`)) {
      return
    }

    setLoading(true)
    setError(null)
    setEmbeddingProgress(0)

    try {
      const response = await fetch(`${apiUrl}/admin/embed?site_id=${siteId}`, {
        method: 'POST',
        headers: getHeaders(),
      })

      if (!response.ok) {
        throw new Error('Embedding failed')
      }

      const data = await response.json()
      const embeddedCount = data.embedded_count || 0
      const duration = Math.round(data.duration_seconds || 0)
      alert(`✅ Successfully embedded ${embeddedCount} pages in ${duration}s`)
      setEmbeddingProgress(100)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Embedding failed')
    } finally {
      setLoading(false)
    }
  }

  if (!apiKey) {
    const isLocalDev = apiUrl.includes('localhost') || apiUrl.includes('127.0.0.1')

    return (
      <>
        <AdminStyles />
        <div className="auth-screen">
          <div className="auth-card">
            <div className="auth-logo">🔐</div>
            <h1>Admin Console</h1>
            <p className="auth-subtitle">
              Sign in with your admin API key to manage <strong>{siteId}</strong> chatbot content
            </p>

            <form onSubmit={handleApiKeySubmit} className="auth-form">
              <div className="form-group">
                <label htmlFor="apiKey">API Key</label>
                <div className="input-group">
                  <span className="input-icon">🔑</span>
                  <input
                    id="apiKey"
                    type={showApiKey ? 'text' : 'password'}
                    value={keyInput}
                    onChange={(e) => setKeyInput(e.target.value)}
                    placeholder="Enter your admin API key"
                    autoFocus
                    required
                  />
                  <button
                    type="button"
                    className="toggle-btn"
                    onClick={() => setShowApiKey(!showApiKey)}
                    title={showApiKey ? 'Hide' : 'Show'}
                  >
                    {showApiKey ? '🙈' : '👁️'}
                  </button>
                </div>
                <small>Your key is stored in session storage only, never persisted to disk</small>
              </div>

              {error && <div className="error-message">⚠️ {error}</div>}

              <button type="submit" className="btn btn-primary auth-submit" disabled={loading}>
                {loading ? (
                  <>
                    <span className="spinner" /> Verifying...
                  </>
                ) : (
                  'Sign In'
                )}
              </button>
            </form>

            {isLocalDev && (
              <div className="info-box">
                <h3>ℹ️ Local Development</h3>
                <p>Use the <code>ADMIN_API_KEY</code> value from your backend's <code>.env</code> file.</p>
              </div>
            )}
          </div>
        </div>
      </>
    )
  }

  return (
    <div className="admin-console">
      <AdminStyles />
      <div className="admin-header">
        <div>
          <h1>📊 Admin Console</h1>
          <p>Site: <strong>{siteId}</strong></p>
        </div>
        <button
          className="logout-btn"
          onClick={() => {
            setApiKey('')
            setKeyInput('')
            sessionStorage.removeItem('admin_api_key')
          }}
        >
          Logout
        </button>
      </div>

      <div className="admin-container">
        {error && <div className="error-message">{error}</div>}

        {/* Stats Bar */}
        <div className="stats-bar">
          <div className="stat">
            <div className="stat-value">{pages.length}</div>
            <div className="stat-label">Total Pages</div>
          </div>
          <div className="stat">
            <div className="stat-value" style={{ color: '#16a34a' }}>
              {selectedCount}
            </div>
            <div className="stat-label">Selected</div>
          </div>
          <div className="stat">
            <div className="stat-value" style={{ color: '#dc2626' }}>
              {pages.filter((p) => p.status === 'excluded').length}
            </div>
            <div className="stat-label">Excluded</div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="action-bar">
          <button
            className="btn btn-secondary"
            onClick={handleRefreshPages}
            disabled={loading}
          >
            🔄 Refresh Pages
          </button>
          <button
            className="btn btn-primary"
            onClick={handleEmbedSelected}
            disabled={loading || selectedCount === 0}
          >
            ⚡ Embed {selectedCount} Selected
          </button>
        </div>

        {/* Embedding Progress */}
        {embeddingProgress > 0 && embeddingProgress < 100 && (
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${embeddingProgress}%` }}>
              {embeddingProgress}%
            </div>
          </div>
        )}

        {/* Pages Table */}
        {loading ? (
          <div className="loading-message">Loading pages...</div>
        ) : pages.length === 0 ? (
          <div className="empty-message">
            <p>No pages found. Click "Refresh Pages" to discover pages from the sitemap.</p>
          </div>
        ) : (
          <div className="pages-table-wrapper">
            <table className="pages-table">
              <thead>
                <tr>
                  <th style={{ width: '40px' }}>
                    <input
                      type="checkbox"
                      checked={pages.every((p) => p.status === 'included')}
                      onChange={handleSelectAll}
                      title="Select/deselect all pages"
                    />
                  </th>
                  <th>Page Title</th>
                  <th>URL</th>
                  <th>Last Scraped</th>
                  <th style={{ width: '100px' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {pages.map((page) => (
                  <tr key={page.url} className={`page-row status-${page.status}`}>
                    <td>
                      <input
                        type="checkbox"
                        checked={page.status === 'included'}
                        onChange={() => togglePageStatus(page.url, page.status)}
                      />
                    </td>
                    <td className="page-title">{page.title || '(Untitled)'}</td>
                    <td className="page-url">
                      <a href={page.url} target="_blank" rel="noopener noreferrer">
                        {new URL(page.url).pathname || '/'}
                      </a>
                    </td>
                    <td className="page-date">
                      {page.last_scraped
                        ? new Date(page.last_scraped).toLocaleDateString()
                        : 'Never'}
                    </td>
                    <td>
                      <span className={`status-badge status-${page.status}`}>
                        {page.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Styles rendered via <AdminStyles /> at the top of each return branch */}
    </div>
  )
}

export default AdminConsole

