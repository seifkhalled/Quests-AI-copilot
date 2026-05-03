export interface User {
  id: string
  email: string
  role: 'candidate' | 'poster'
  created_at: string
}

export interface Conversation {
  id: string
  user_id: string
  title: string | null
  scope: 'global' | 'document_scoped'
  scoped_document_id: string | null
  status: 'active' | 'ended'
  created_at: string
  last_message_at: string
}

export interface Message {
  id: string
  conversation_id: string
  role: 'user' | 'assistant'
  content: string
  sources: Source[]
  confidence: number | null
  reasoning: string | null
  created_at: string
}

export interface Source {
  document_title: string
  chunk_index: number
  snippet: string
  score?: number
}

export interface Document {
  id: string
  title: string
  source_type: 'pdf' | 'txt' | 'md' | 'slack_json'
  status: 'pending' | 'processing' | 'processed' | 'failed'
  chunk_count: number
  file_url: string | null
  created_at: string
}

export interface AuthResponse {
  token: string
  user: User
}

export interface ChatResponse {
  answer: string
  sources: Source[]
  confidence: number | null
  intent: string | null
  conversation_id: string
}