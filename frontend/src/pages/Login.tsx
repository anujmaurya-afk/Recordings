import { useState, useRef, useEffect } from 'react'
import { login } from '../services/authApi'

interface LoginProps {
  onLogin: () => void
  onNavigateToSignUp: () => void
  initialEmail?: string
}

export default function Login({ onLogin, onNavigateToSignUp, initialEmail = '' }: LoginProps) {
  const [email, setEmail]       = useState(initialEmail)
  const [password, setPassword] = useState('')
  const [error, setError]       = useState<string | null>(null)
  const [loading, setLoading]   = useState(false)
  const [shake, setShake]       = useState(false)
  const emailInputRef = useRef<HTMLInputElement>(null)
  const passwordInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (initialEmail) {
      setEmail(initialEmail)
      passwordInputRef.current?.focus()
    } else {
      emailInputRef.current?.focus()
    }
  }, [initialEmail])

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault()
    setError(null)

    const cleanEmail = email.trim().toLowerCase()
    if (!cleanEmail) {
      setError('Please enter your email.')
      triggerShake()
      emailInputRef.current?.focus()
      return
    }

    if (!password) {
      setError('Please enter your password.')
      triggerShake()
      passwordInputRef.current?.focus()
      return
    }

    setLoading(true)

    try {
      await login(cleanEmail, password)
      onLogin()
    } catch (err: any) {
      setLoading(false)
      setError(err?.message || 'Incorrect email or password. Please try again.')
      triggerShake()
      setPassword('')
      passwordInputRef.current?.focus()
    }
  }

  const triggerShake = () => {
    setShake(true)
    setTimeout(() => setShake(false), 500)
  }

  return (
    <div className="login-screen">
      {/* Animated ambient orbs */}
      <div className="login-orb login-orb-1" />
      <div className="login-orb login-orb-2" />
      <div className="login-orb login-orb-3" />

      <div className={`login-card${shake ? ' shake' : ''}`}>
        {/* Logo */}
        <div className="login-logo">
          <div className="login-logo-icon">🎙</div>
          <div>
            <div className="login-title">Recording Converter</div>
            <div className="login-subtitle">Sign in to your account</div>
          </div>
        </div>

        {/* Form */}
        <form className="login-form" onSubmit={handleSubmit}>
          {/* Email field */}
          <div className="login-input-wrap">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16" height="16" viewBox="0 0 24 24"
              fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            >
              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
              <polyline points="22,6 12,13 2,6" />
            </svg>
            <input
              ref={emailInputRef}
              id="login-email"
              className="login-input"
              type="email"
              placeholder="Email address"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value)
                if (error) setError(null)
              }}
              autoComplete="email"
              required
            />
          </div>

          {/* Password field */}
          <div className="login-input-wrap">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16" height="16" viewBox="0 0 24 24"
              fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            >
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <input
              ref={passwordInputRef}
              id="login-password"
              className="login-input"
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value)
                if (error) setError(null)
              }}
              autoComplete="current-password"
              required
            />
          </div>

          {error && (
            <div className="login-error" role="alert">
              <span>🔒</span>
              {error}
            </div>
          )}

          <button
            id="login-submit"
            type="submit"
            className="login-btn"
            disabled={loading || !email.trim() || !password}
          >
            {loading ? (
              <>
                <span className="spin" style={{ display: 'inline-block', marginRight: 6 }}>⟳</span>
                Signing In…
              </>
            ) : (
              'Sign In'
            )}
          </button>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
            marginTop: 18,
            fontSize: '0.84rem',
            color: 'var(--text-muted)'
          }}>
            <span>Don't have an account?</span>
            <button
              type="button"
              id="login-to-signup"
              onClick={onNavigateToSignUp}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--accent-2)',
                fontWeight: 600,
                cursor: 'pointer',
                padding: 0,
                fontSize: 'inherit'
              }}
            >
              Create one
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
