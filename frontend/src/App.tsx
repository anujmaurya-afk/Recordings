import { useState, useEffect } from 'react'
import Home from './pages/Home'
import Login from './pages/Login'
import SignUp from './pages/SignUp'
import NewJob from './pages/NewJob'
import JobDetail from './pages/JobDetail'
import { isAuthenticated, logout, getUserEmail } from './services/authApi'

type Route =
  | { name: 'home' }
  | { name: 'newJob'; mode: 'paste' | 'csv' | 'excel' }
  | { name: 'jobDetail'; jobId: string }

function getRouteFromUrl(): Route {
  const hash = window.location.hash.replace(/^#/, '')
  const params = new URLSearchParams(window.location.search)
  const jobId = params.get('jobId') || (hash.startsWith('job=') ? hash.replace('job=', '') : (hash.startsWith('JOB-') ? hash : null))
  if (jobId) {
    return { name: 'jobDetail', jobId }
  }
  return { name: 'home' }
}

export default function App() {
  const [authed, setAuthed] = useState(isAuthenticated)
  const [authScreen, setAuthScreen] = useState<'login' | 'signup'>('login')
  const [prefilledEmail, setPrefilledEmail] = useState('')
  const [userEmail, setUserEmail] = useState<string | null>(getUserEmail)
  const [route, setRoute] = useState<Route>(getRouteFromUrl)

  useEffect(() => {
    setUserEmail(getUserEmail())
  }, [authed])

  useEffect(() => {
    const onHashChange = () => setRoute(getRouteFromUrl())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  const handleLoginSuccess = () => {
    setAuthed(true)
    setUserEmail(getUserEmail())
  }

  const handleRegistered = (email: string) => {
    setPrefilledEmail(email)
  }

  const navigateTo = (newRoute: Route) => {
    setRoute(newRoute)
    if (newRoute.name === 'jobDetail') {
      window.location.hash = `job=${newRoute.jobId}`
    } else {
      window.location.hash = ''
    }
  }

  const handleSignOut = async () => {
    await logout()
    setAuthed(false)
    setAuthScreen('login')
    navigateTo({ name: 'home' })
  }

  if (!authed) {
    if (authScreen === 'signup') {
      return (
        <SignUp
          onNavigateToLogin={() => setAuthScreen('login')}
          onRegisteredSuccess={handleRegistered}
        />
      )
    }
    return (
      <Login
        onLogin={handleLoginSuccess}
        onNavigateToSignUp={() => setAuthScreen('signup')}
        initialEmail={prefilledEmail}
      />
    )
  }

  const nav = {
    home:      () => navigateTo({ name: 'home' }),
    newJob:    (mode: 'paste' | 'csv' | 'excel') => navigateTo({ name: 'newJob', mode }),
    jobDetail: (jobId: string) => navigateTo({ name: 'jobDetail', jobId }),
  }

  return (
    <>
      <nav className="nav">
        <div className="nav-logo" onClick={nav.home} style={{ cursor: 'pointer' }}>
          <div className="nav-logo-icon">🎙</div>
          Recording Converter
        </div>
        <span className="nav-spacer" />
        {userEmail && (
          <span
            style={{
              fontSize: '0.8rem',
              color: 'var(--text-secondary)',
              background: 'rgba(255, 255, 255, 0.05)',
              padding: '5px 12px',
              borderRadius: '20px',
              border: '1px solid var(--border-subtle)',
              maxWidth: '220px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
            title={userEmail}
          >
            👤 {userEmail}
          </span>
        )}
        <span className="nav-pill">S3 → Presigned URL</span>
        <button
          id="nav-signout"
          className="nav-signout"
          onClick={handleSignOut}
          title="Sign out"
        >
          Sign Out
        </button>
      </nav>

      {route.name === 'home' && <Home onSelectMode={nav.newJob} onSelectJob={nav.jobDetail} />}
      {route.name === 'newJob' && (
        <NewJob
          mode={route.mode}
          onJobCreated={nav.jobDetail}
          onBack={nav.home}
        />
      )}
      {route.name === 'jobDetail' && (
        <JobDetail jobId={route.jobId} onBack={nav.home} />
      )}
    </>
  )
}
