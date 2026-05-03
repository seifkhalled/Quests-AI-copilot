'use client'

import { useState, useEffect } from 'react'
import { User } from '@/lib/types'
import { getCurrentUser, isAuthenticated, clearAuth } from '@/lib/auth'

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const currentUser = getCurrentUser()
    setUser(currentUser)
    setLoading(false)
  }, [])

  const logout = () => {
    clearAuth()
    setUser(null)
    window.location.href = '/login'
  }

  return {
    user,
    loading,
    isAuthenticated: loading ? false : !!user,
    logout
  }
}