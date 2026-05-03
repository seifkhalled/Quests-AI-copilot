'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { createConversation, endConversation, sendMessageStream } from '@/lib/api'
import { getCurrentUser } from '@/lib/auth'
import type { Message, Conversation, User, Source } from '@/lib/types'

export function useChat() {
  const [user, setUser] = useState<User | null>(null)
  const [conversation, setConversation] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [mounted, setMounted] = useState(false)
  const streamAbortRef = useRef<(() => void) | null>(null)
  const startedRef = useRef(false)

  useEffect(() => {
    setMounted(true)
    setUser(getCurrentUser())
  }, [])

  useEffect(() => { if (mounted && user) startConversation() }, [mounted, user])

  async function startConversation() {
    if (!user) { setError('Not logged in'); return }
    if (startedRef.current) return  // prevent duplicate calls
    startedRef.current = true
    setLoading(true)
    setError('')
    try {
      const res = await createConversation(user.id, 'global')
      setConversation(res.data)
      setMessages([])
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || 'Could not start conversation'
      setError(detail)
      startedRef.current = false  // allow retry
    }
    finally { setLoading(false) }
  }

  async function send(text: string) {
    if (!conversation || !user || sending) return
    setSending(true)
    const optimistic: Message = {
      id: crypto.randomUUID(),
      conversation_id: conversation.id,
      role: 'user', content: text,
      sources: [], confidence: null, reasoning: null,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, optimistic])

    const streamMessage: Message = {
      id: crypto.randomUUID(),
      conversation_id: conversation.id,
      role: 'assistant', content: '',
      sources: [], confidence: null, reasoning: null,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, streamMessage])

    try {
      let fullContent = ''
      let sources: Source[] = []
      let statusMsg = ''

      streamAbortRef.current = sendMessageStream(
        conversation.id,
        user.id,
        text,
        (chunk, type) => {
          if (type === 'status') {
            statusMsg = chunk
          } else if (type === 'content') {
            fullContent += chunk
            setMessages(prev => prev.map(m =>
              m.id === streamMessage.id ? { ...m, content: fullContent } : m
            ))
          } else if (type === 'sources') {
            try {
              sources = JSON.parse(chunk)
              setMessages(prev => prev.map(m =>
                m.id === streamMessage.id ? { ...m, sources } : m
              ))
            } catch {}
          } else if (type === 'error') {
            setError(chunk)
          }
        }
      )
    } catch {
      setError('Failed to send message')
      setMessages(prev => prev.filter(m => m.id !== optimistic.id))
    } finally { setSending(false) }
  }

  function abortStream() {
    streamAbortRef.current?.()
    streamAbortRef.current = null
  }

  async function newChat() {
    abortStream()
    if (conversation && user) {
      await endConversation(conversation.id, user.id).catch(() => {})
    }
    startedRef.current = false  // allow a new conversation to be started
    await startConversation()
  }

  return { conversation, messages, loading, sending, error, send, newChat, abortStream }
}