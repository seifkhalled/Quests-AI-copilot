'use client'
import { useEffect, useCallback, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getCurrentUser, clearAuth } from '@/lib/auth'
import { useDocuments } from '@/hooks/useDocuments'
import type { Document, User } from '@/lib/types'

export default function DashboardPage() {
  const router = useRouter()
  const [mounted, setMounted] = useState(false)
  const [user, setUser] = useState<User | null>(null)
  const { documents, loading, uploading, uploadError, upload } = useDocuments()

  useEffect(() => {
    setMounted(true)
    setUser(getCurrentUser())
  }, [])

  useEffect(() => {
    if (!mounted) return
    if (!user) { router.push('/login'); return }
    if (user.role === 'candidate') router.push('/chat')
  }, [mounted, user, router])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    const files = Array.from(e.dataTransfer.files).filter(f =>
      f.type === 'application/pdf' ||
      f.type === 'text/plain' ||
      f.name.endsWith('.md')
    )
    if (files.length) await upload(files)
  }, [upload])

  const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    if (files.length) await upload(files)
    e.target.value = ''
  }

  const stats = {
    total:      documents.length,
    processed:  documents.filter(d => d.status === 'processed').length,
    processing: documents.filter(d => ['processing','pending'].includes(d.status)).length,
    failed:     documents.filter(d => d.status === 'failed').length,
  }

  if (!mounted) return null

  return (
    <div className="dashboard-layout">
      <nav className="dash-nav">
        <div className="nav-brand">
          <span className="brand-logo-sm">QC</span>
          <span className="brand-name">Quest Copilot</span>
          <span className="role-pill">Poster</span>
        </div>
        <div className="nav-right">
          <span className="nav-email">{user?.email}</span>
          <button className="logout-btn"
            onClick={() => { clearAuth(); router.push('/login') }}>
            Sign out
          </button>
        </div>
      </nav>

      <div className="dash-body">
        <div className="page-heading">
          <h1 className="page-title">Knowledge Base</h1>
          <p className="page-sub">Upload quest documents to the AI knowledge base</p>
        </div>

        <div className="stats-row">
          {[
            { label: 'Total',      value: stats.total,      cls: '' },
            { label: 'Processed',  value: stats.processed,  cls: 'stat-success' },
            { label: 'Processing', value: stats.processing, cls: 'stat-warning' },
            { label: 'Failed',     value: stats.failed,     cls: 'stat-danger'  },
          ].map(s => (
            <div key={s.label} className="stat-card">
              <span className={`stat-value ${s.cls}`}>{s.value}</span>
              <span className="stat-label">{s.label}</span>
            </div>
          ))}
        </div>

        <div
          className={`upload-zone ${uploading ? 'uploading' : ''}`}
          onDrop={handleDrop}
          onDragOver={e => e.preventDefault()}>
          <div className="upload-icon">📁</div>
          <p className="upload-title">
            {uploading ? 'Uploading and processing...' : 'Drop quest files here'}
          </p>
          <p className="upload-sub">PDF, TXT, or Markdown — multiple files supported</p>
          <label className="upload-pick-btn">
            Browse files
            <input type="file" multiple
              accept=".pdf,.txt,.md,text/plain,application/pdf"
              onChange={handleFileInput}
              disabled={uploading}
              style={{ display: 'none' }} />
          </label>
          {uploadError && <p className="upload-error">{uploadError}</p>}
        </div>

        <div className="doc-section">
          <div className="doc-section-head">
            <h2 className="doc-section-title">Documents</h2>
            <span className="doc-count">{documents.length} total</span>
          </div>

          {loading && <p className="loading-msg">Loading documents...</p>}

          {!loading && documents.length === 0 && (
            <div className="empty-docs">
              No documents yet — upload your first quest file above.
            </div>
          )}

          <div className="doc-list">
            {documents.map(doc => <DocRow key={doc.id} doc={doc} />)}
          </div>
        </div>
      </div>
    </div>
  )
}

function DocRow({ doc }: { doc: Document }) {
  const color = {
    processed: 'success',
    pending:   'warning',
    processing:'warning',
    failed:    'danger'
  }[doc.status] || 'warning'

  return (
    <div className="doc-row">
      <div className="doc-info">
        <span className="doc-title">{doc.title}</span>
        <span className="doc-meta">
          {doc.source_type.toUpperCase()} · {doc.chunk_count} chunks ·{' '}
          {new Date(doc.created_at).toLocaleDateString()}
        </span>
      </div>
      <div className="doc-right">
        <span className={`status-badge status-${color}`}>{doc.status}</span>
        {doc.file_url && (
          <a href={doc.file_url} target="_blank" rel="noopener noreferrer"
            className="doc-link">View</a>
        )}
      </div>
    </div>
  )
}