import axios from 'axios'
import { getToken } from './auth'

const BASE = process.env.NEXT_PUBLIC_API_URL

const client = axios.create({ baseURL: BASE })

client.interceptors.request.use(config => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export const registerUser = (email: string, password: string, role: string) =>
  client.post('/api/auth/register', { email, password, role })

export const loginUser = (email: string, password: string) =>
  client.post('/api/auth/login', { email, password })

export const createConversation = (user_id: string, scope = 'global') =>
  client.post('/api/conversations', { user_id, scope })

export const getMessages = (conversation_id: string, user_id: string) =>
  client.get(`/api/chat/${conversation_id}/messages`, { params: { user_id } })

export const endConversation = (conversation_id: string, user_id: string) =>
  client.post(`/api/chat/${conversation_id}/end`, null, { params: { user_id } })

export const sendMessage = (conversation_id: string, user_id: string, message: string) =>
  client.post('/api/chat', { conversation_id, user_id, message })

export const getDocuments = (status?: string) =>
  client.get('/api/documents', { params: status ? { status } : {} })

export const getDocument = (id: string) =>
  client.get(`/api/documents/${id}`)

export const uploadFiles = (files: File[]) => {
  const form = new FormData()
  files.forEach(f => form.append('files', f))
  return client.post('/api/ingest/files', form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const getInsights = () =>
  client.get('/api/ai/insights')