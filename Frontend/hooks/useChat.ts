'use client'

import { useState, useEffect } from 'react'
import { createConversation, sendMessage, endConversation } from '@/lib/api'
import { getCurrentUser } from '@/lib/auth'
import type { Message, Conversation, User } from '@/lib/types'

export function useChat() {
  const [user, setUser] = useState<User | null>(null)
  const [conversation, setConversation] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    setUser(getCurrentUser())
  }, [])

  useEffect(() => { if (mounted && user) startConversation() }, [mounted, user])

  async function startConversation() {
    if (!user) return
    setLoading(true)
    try {
      const res = await createConversation(user.id, 'global')
      setConversation(res.data)
      setMessages([])
    } catch { setError('Could not start conversation') }
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
    try {
      const res = await sendMessage(conversation.id, user.id, text)
      const d = res.data
      const assistant: Message = {
        id: crypto.randomUUID(),
        conversation_id: conversation.id,
        role: 'assistant', content: d.answer,
        sources: d.sources || [], confidence: d.confidence,
        reasoning: null, created_at: new Date().toISOString(),
      }
      setMessages(prev => [...prev, assistant])
    } catch {
      setError('Failed to send message')
      setMessages(prev => prev.filter(m => m.id !== optimistic.id))
    } finally { setSending(false) }
  }

  async function newChat() {
    if (conversation && user) {
      await endConversation(conversation.id, user.id).catch(() => {})
    }
    await startConversation()
  }

  return { conversation, messages, loading, sending, error, send, newChat }
}