'use client'

import { Document } from '@/lib/types'
import { Badge } from '@/components/ui/Badge'

interface DocumentStatusBadgeProps {
  status: Document['status']
}

export function DocumentStatusBadge({ status }: DocumentStatusBadgeProps) {
  const labels = {
    pending: 'Pending',
    processing: 'Processing',
    processed: 'Ready',
    failed: 'Failed'
  }

  return (
    <Badge variant={status}>
      {status === 'processing' && <span className="w-2 h-2 rounded-full bg-[#6c63ff] animate-pulse" />}
      {labels[status]}
    </Badge>
  )
}