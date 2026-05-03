'use client'

import { ReactNode } from 'react'

interface BadgeProps {
  variant?: 'pending' | 'processing' | 'processed' | 'failed' | 'default'
  children: ReactNode
  className?: string
}

export function Badge({ variant = 'default', children, className = '' }: BadgeProps) {
  const variants = {
    pending: 'bg-[#f59e0b] text-black',
    processing: 'bg-[#6c63ff22] text-[#6c63ff]',
    processed: 'bg-[#22c55e] text-black',
    failed: 'bg-[#ef4444] text-white',
    default: 'bg-[#1a1a24] text-[#8888a8] border border-[#2a2a38]'
  }

  return (
    <span 
      className={`
        inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
        ${variants[variant]}
        ${className}
      `}
    >
      {children}
    </span>
  )
}