'use client'

import { Message } from '@/lib/types'

interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  
  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className={`message ${message.role}`}>
      <div className="message-content">
        {message.content}
      </div>
      <span className="message-time">
        {formatTime(message.created_at)}
      </span>
    </div>
  )
}