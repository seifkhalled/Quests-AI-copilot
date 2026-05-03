'use client'

import { Document } from '@/lib/types'
import { DocumentStatusBadge } from './DocumentStatusBadge'

interface DocumentListProps {
  documents: Document[]
  loading?: boolean
}

export function DocumentList({ documents, loading }: DocumentListProps) {
  const getFileIcon = (type: string) => {
    switch (type) {
      case 'pdf': return '📕'
      case 'txt': return '📝'
      case 'md': return '📋'
      case 'slack_json': return '💬'
      default: return '📄'
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="loading-spinner" />
      </div>
    )
  }

  if (documents.length === 0) {
    return (
      <div className="text-center py-12 text-[#5a5a78]">
        No documents uploaded yet
      </div>
    )
  }

  return (
    <div className="document-list">
      {documents.map((doc) => (
        <div key={doc.id} className="document-item">
          <div className="document-icon">
            {getFileIcon(doc.source_type)}
          </div>
          <div className="document-info">
            <div className="document-name">{doc.title}</div>
            <div className="document-meta">
              {doc.source_type.toUpperCase()} • {doc.chunk_count} chunks • {formatDate(doc.created_at)}
            </div>
          </div>
          <DocumentStatusBadge status={doc.status} />
        </div>
      ))}
    </div>
  )
}