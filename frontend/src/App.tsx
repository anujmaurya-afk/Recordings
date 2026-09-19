import { useState, useEffect } from 'react'
import Home from './pages/Home'
import NewJob from './pages/NewJob'
import JobDetail from './pages/JobDetail'

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
  const [route, setRoute] = useState<Route>(getRouteFromUrl)

  useEffect(() => {
    const onHashChange = () => setRoute(getRouteFromUrl())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  const navigateTo = (newRoute: Route) => {
    setRoute(newRoute)
    if (newRoute.name === 'jobDetail') {
      window.location.hash = `job=${newRoute.jobId}`
    } else {
      window.location.hash = ''
    }
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
        <span className="nav-pill">S3 → Presigned URL</span>
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
