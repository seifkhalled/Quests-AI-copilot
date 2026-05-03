'use client'

import { Message } from '@/lib/types'
import { MessageBubble } from './MessageBubble'
import { SourcePanel } from './SourcePanel'

interface ChatWindowProps {
  messages: Message[]
  loading?: boolean
}

export function ChatWindow({ messages, loading }: ChatWindowProps) {
  if (loading) {
    return (
      <div className="chat-messages">
        <div className="flex items-center justify-center h-full">
          <div className="loading-spinner" />
        </div>
      </div>
    )
  }

  if (messages.length === 0) {
    return (
      <div className="chat-messages">
        <div className="flex flex-col items-center justify-center h-full text-center">
          <div className="text-4xl mb-4">💬</div>
          <h3 className="text-lg font-semibold mb-2">Start a conversation</h3>
          <p className="text-[#8888a8] text-sm max-w-md">
            Ask me anything about the job descriptions, requirements, or company culture.
            I&apos;ll search through your uploaded documents to find the best answers.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="chat-messages">
      {messages.map((message) => (
        <div key={message.id}>
          <MessageBubble message={message} />
          {message.sources.length > 0 && message.role === 'assistant' && (
            <SourcePanel sources={message.sources} />
          )}
        </div>
      ))}
    </div>
  )
}