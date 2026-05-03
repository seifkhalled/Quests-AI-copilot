import { User } from './types'

const TOKEN_KEY = 'qc_token'
const USER_KEY = 'qc_user'

export function saveAuth(token: string, user: User) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function getCurrentUser(): User | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try { return JSON.parse(raw) } catch { return null }
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function isAuthenticated(): boolean {
  return !!getToken()
}