'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { loginUser } from '@/lib/api'
import { saveAuth } from '@/lib/auth'
import Link from 'next/link'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await loginUser(email, password)
      const { access_token, user } = res.data
      saveAuth(access_token, user)
      router.push(user.role === 'candidate' ? '/chat' : '/dashboard')
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-layout">
      <div className="auth-brand">
        <div className="brand-content">
          <div className="brand-logo">QC</div>
          <h1 className="brand-title">Quest Copilot</h1>
          <p className="brand-sub">
            AI-powered hiring intelligence.
            Find your perfect quest.
          </p>
        </div>
      </div>
      <div className="auth-form-panel">
        <div className="auth-form-card">
          <h2 className="form-title">Welcome back</h2>
          <p className="form-sub">Sign in to your account</p>
          {error && <div className="form-error">{error}</div>}
          <form onSubmit={handleSubmit} className="form-body">
            <div className="field">
              <label className="field-label">Email</label>
              <input type="email" className="field-input"
                placeholder="you@example.com"
                value={email} onChange={e => setEmail(e.target.value)} required />
            </div>
            <div className="field">
              <label className="field-label">Password</label>
              <input type="password" className="field-input"
                placeholder="••••••••"
                value={password} onChange={e => setPassword(e.target.value)} required />
            </div>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
          <p className="form-footer">
            No account? <Link href="/register" className="form-link">Create one</Link>
          </p>
        </div>
      </div>
    </div>
  )
}