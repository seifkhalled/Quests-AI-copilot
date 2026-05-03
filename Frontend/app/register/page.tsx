'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { registerUser } from '@/lib/api'
import { saveAuth } from '@/lib/auth'
import Link from 'next/link'

export default function RegisterPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<'candidate' | 'poster'>('candidate')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await registerUser(email, password, role)
      const { access_token, user } = res.data
      saveAuth(access_token, user)
      router.push(user.role === 'candidate' ? '/chat' : '/dashboard')
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Registration failed')
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
          <p className="brand-sub">Challenge-based hiring, powered by AI.</p>
        </div>
      </div>
      <div className="auth-form-panel">
        <div className="auth-form-card">
          <h2 className="form-title">Create account</h2>
          <p className="form-sub">Choose your role to get started</p>

          <div className="role-selector">
            <button type="button"
              className={`role-card ${role === 'candidate' ? 'role-active' : ''}`}
              onClick={() => setRole('candidate')}>
              <span className="role-icon">🎯</span>
              <span className="role-name">Candidate</span>
              <span className="role-desc">Find quests that match you</span>
            </button>
            <button type="button"
              className={`role-card ${role === 'poster' ? 'role-active' : ''}`}
              onClick={() => setRole('poster')}>
              <span className="role-icon">📋</span>
              <span className="role-name">Poster</span>
              <span className="role-desc">Post quests and manage hiring</span>
            </button>
          </div>

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
                placeholder="Min. 8 characters"
                value={password} onChange={e => setPassword(e.target.value)}
                minLength={8} required />
            </div>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Creating account...' : `Join as ${role}`}
            </button>
          </form>
          <p className="form-footer">
            Already have an account?{' '}
            <Link href="/login" className="form-link">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}