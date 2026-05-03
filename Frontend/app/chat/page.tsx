'use client'
import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { getCurrentUser, clearAuth } from '@/lib/auth'
import { useChat } from '@/hooks/useChat'
import type { Source, Message, User } from '@/lib/types'

export const dynamic = 'force-dynamic'

export default function ChatPage() {
  const router = useRouter()
  const [mounted, setMounted] = useState(false)
  const [user, setUser] = useState<User | null>(null)
  const { messages, sending, error, send, newChat } = useChat()
  const [input, setInput] = useState('')
  const [activeSources, setActiveSources] = useState<Source[] | null>(null)
  const [activeConfidence, setActiveConfidence] = useState<number | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setMounted(true)
    setUser(getCurrentUser())
  }, [])

  useEffect(() => { if (mounted && !user) router.push('/login') }, [mounted, user])
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend() {
    if (!input.trim() || sending) return
    const text = input.trim()
    setInput('')
    await send(text)
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const SUGGESTIONS = [
    'What backend quests are available?',
    'I have 2 years React experience — what matches me?',
    'What salary ranges are offered?',
  ]

  return (
    <div className="chat-layout">
      <aside className="chat-sidebar">
        <div className="sidebar-brand">
          <span className="brand-logo-sm">QC</span>
          <span className="brand-name">Quest Copilot</span>
        </div>
        <div className="sidebar-user">
          <div className="user-avatar">{user?.email?.[0]?.toUpperCase()}</div>
          <div className="user-info">
            <span className="user-email">{user?.email}</span>
            <span className="user-role-tag">Candidate</span>
          </div>
        </div>
        <button className="sidebar-btn" onClick={newChat}>+ New conversation</button>
        <div style={{ flex: 1 }} />
        <button className="logout-btn"
          onClick={() => { clearAuth(); router.push('/login') }}>
          Sign out
        </button>
      </aside>

      <main className="chat-main">
        <div className="chat-header">
          <h1 className="chat-title">Quest Assistant</h1>
          <p className="chat-sub">Ask about available quests, requirements, or salary ranges</p>
        </div>

        <div className="messages-container">
          {messages.length === 0 && (
            <div className="empty-state">
              <div className="empty-icon"></div>
              <p className="empty-title">Start exploring quests</p>
              <p className="empty-sub">Ask me anything about available roles</p>
              <div className="suggestion-chips">
                {SUGGESTIONS.map(s => (
                  <button key={s} className="chip" onClick={() => setInput(s)}>{s}</button>
                ))}
              </div>
            </div>
          )}

          {messages.map(msg => (
            <div key={msg.id}
              className={`message-row ${msg.role === 'user' ? 'message-user' : 'message-assistant'}`}>
              {msg.role === 'assistant' && <div className="msg-avatar">QC</div>}
              <div className="msg-body">
                <div className={`bubble ${msg.role === 'user' ? 'bubble-user' : 'bubble-assistant'}`}>
                  {msg.content}
                </div>
                {msg.role === 'assistant' && msg.sources?.length > 0 && (
                  <button className="sources-btn"
                    onClick={() => {
                      setActiveSources(msg.sources)
                      setActiveConfidence(msg.confidence)
                    }}>
                    {msg.sources.length} source{msg.sources.length > 1 ? 's' : ''} -&gt;
                  </button>
                )}
              </div>
            </div>
          ))}

          {sending && (
            <div className="message-row message-assistant">
              <div className="msg-avatar">QC</div>
              <div className="typing-indicator">
                <span /><span /><span />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {error && <div className="chat-error">{error}</div>}

        <div className="chat-input-bar">
          <textarea className="chat-textarea" rows={1}
            placeholder="Ask about quests, requirements, salaries..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            disabled={sending} />
          <button className="send-btn"
            onClick={handleSend}
            disabled={!input.trim() || sending}>
            {sending ? '...' : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            )}
          </button>
        </div>
      </main>

      {activeSources && activeSources.length > 0 && (
        <aside className="source-panel">
          <div className="source-header">
            <span className="source-title">Sources</span>
            {activeConfidence !== null && (
              <span className="confidence-badge">
                {Math.round(activeConfidence * 100)}% confidence
              </span>
            )}
            <button className="source-close" onClick={() => setActiveSources(null)}>x</button>
          </div>
          <div className="source-list">
            {activeSources.map((s, i) => (
              <div key={i} className="source-card">
                <div className="source-doc">{s.document_title}</div>
                <div className="source-chunk">Chunk {s.chunk_index}</div>
                <div className="source-snippet">
                  {s.snippet && s.snippet.length > 150 
                    ? s.snippet.slice(0, 150) + '...' 
                    : s.snippet}
                </div>
              </div>
            ))}
          </div>
        </aside>
      )}
    </div>
  )
}