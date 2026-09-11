import { useState, useRef, useEffect } from 'react'
import { register } from '../services/authApi'

interface SignUpProps {
  onNavigateToLogin: () => void
  onRegisteredSuccess?: (email: string) => void
}

export default function SignUp({ onNavigateToLogin, onRegisteredSuccess }: SignUpProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [shake, setShake] = useState(false)
  const emailInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    emailInputRef.current?.focus()
  }, [])

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault()
    setError(null)

    const cleanEmail = email.trim().toLowerCase()
    if (!cleanEmail || !cleanEmail.includes('@')) {
      setError('Please enter a valid email address.')
      triggerShake()
      return
    }

    if (!cleanEmail.endsWith('@credresolve.com')) {
      setError('Registration is restricted to @credresolve.com email addresses only.')
      triggerShake()
      return
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters.')
      triggerShake()
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      triggerShake()
      return
    }

    setLoading(true)

    try {
      await register(cleanEmail, password)
      setSuccess(true)
      if (onRegisteredSuccess) {
        onRegisteredSuccess(cleanEmail)
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to create account. Please try again.')
      triggerShake()
    } finally {
      setLoading(false)
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
            <div className="login-title">Create Account</div>
            <div className="login-subtitle">Sign up to convert recording URLs</div>
          </div>
        </div>

        {success ? (
          <div style={{ textAlign: 'center', padding: '16px 8px' }}>
            <div style={{ fontSize: '3rem', marginBottom: 12 }}>🎉</div>
            <h3 style={{ margin: '0 0 8px 0', fontSize: '1.25rem', color: '#f8fafc' }}>
              Account Created!
            </h3>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 20 }}>
              Your account (<strong style={{ color: 'var(--accent-2)' }}>{email}</strong>) has been created successfully. You can now sign in to your dashboard.
            </p>
            <button
              id="signup-proceed-login"
              type="button"
              className="login-btn"
              onClick={onNavigateToLogin}
            >
              Sign In to Continue
            </button>
          </div>
        ) : (
          /* Sign up form */
          <form className="login-form" onSubmit={handleSubmit}>
            {/* Email field */}
            <div className="login-input-wrap">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                <polyline points="22,6 12,13 2,6" />
              </svg>
              <input
                ref={emailInputRef}
                id="signup-email"
                className="login-input"
                type="email"
                placeholder="name@credresolve.com"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value)
                  if (error) setError(null)
                }}
                autoComplete="email"
                required
              />
            </div>

            <div style={{
              fontSize: '0.75rem',
              color: 'var(--accent-2)',
              marginTop: -6,
              marginBottom: 2,
              textAlign: 'left',
              paddingLeft: 4,
              display: 'flex',
              alignItems: 'center',
              gap: 4
            }}>
              <span>🔒</span> Only @credresolve.com accounts permitted
            </div>

            {/* Password field */}
            <div className="login-input-wrap">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <input
                id="signup-password"
                className="login-input"
                type="password"
                placeholder="Password (min. 6 characters)"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value)
                  if (error) setError(null)
                }}
                autoComplete="new-password"
                required
              />
            </div>

            {/* Confirm Password field */}
            <div className="login-input-wrap">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              <input
                id="signup-confirm-password"
                className="login-input"
                type="password"
                placeholder="Confirm Password"
                value={confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(e.target.value)
                  if (error) setError(null)
                }}
                autoComplete="new-password"
                required
              />
            </div>

            {error && (
              <div className="login-error" role="alert">
                <span>⚠️</span>
                {error}
              </div>
            )}

            <button
              id="signup-submit"
              type="submit"
              className="login-btn"
              disabled={loading || !email.trim() || !password || !confirmPassword}
            >
              {loading ? (
                <>
                  <span className="spin" style={{ display: 'inline-block', marginRight: 6 }}>⟳</span>
                  Creating Account…
                </>
              ) : (
                'Create Account'
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
              <span>Already have an account?</span>
              <button
                type="button"
                id="signup-to-login"
                onClick={onNavigateToLogin}
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
                Sign In
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
