'use client'

import { Source } from '@/lib/types'

interface SourcePanelProps {
  sources: Source[]
}

export function SourcePanel({ sources }: SourcePanelProps) {
  if (sources.length === 0) return null

  return (
    <div className="sources-panel">
      <div className="sources-title">Sources</div>
      {sources.map((source, idx) => (
        <div key={idx} className="source-item">
          <div className="font-medium text-[#e8e8f0] mb-1">
            {source.document_title}
          </div>
          <div className="text-[#8888a8] text-xs line-clamp-2">
            {source.snippet}
          </div>
        </div>
      ))}
    </div>
  )
}