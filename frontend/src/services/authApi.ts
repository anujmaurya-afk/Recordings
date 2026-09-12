const BASE = 'https://recordings-ruby.vercel.app/api/auth'

export interface AuthResponse {
  token: string
  email: string
  user_id: number
}

export interface UserInfo {
  id: number
  email: string
  created_at: string
}

export interface RegisterResponse {
  message: string
  email: string
}

export function getToken(): string | null {
  return localStorage.getItem('rc_token')
}

export function getUserEmail(): string | null {
  return localStorage.getItem('rc_email')
}

export function setSession(token: string, email: string): void {
  localStorage.setItem('rc_token', token)
  localStorage.setItem('rc_email', email)
  localStorage.setItem('rc_auth', '1')
}

export function clearSession(): void {
  localStorage.removeItem('rc_token')
  localStorage.removeItem('rc_email')
  localStorage.removeItem('rc_auth')
}

export function isAuthenticated(): boolean {
  return !!getToken()
}

export async function login(
  email: string,
  password: string
): Promise<AuthResponse> {
  const res = await fetch(`${BASE}/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: email.trim(),
      password,
    }),
  })

  if (!res.ok) {
    let detail = `Login failed (${res.status})`

    try {
      const data = await res.json()
      detail = data.detail ?? detail
    } catch {}

    throw new Error(detail)
  }

  const data: AuthResponse = await res.json()

  setSession(data.token, data.email)

  return data
}

export async function register(
  email: string,
  password: string
): Promise<RegisterResponse> {
  const res = await fetch(`${BASE}/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: email.trim(),
      password,
    }),
  })

  if (!res.ok) {
    let detail = `Sign up failed (${res.status})`

    try {
      const data = await res.json()
      detail = data.detail ?? detail
    } catch {}

    throw new Error(detail)
  }

  return res.json()
}

export async function logout(): Promise<void> {
  const token = getToken()

  if (token) {
    try {
      await fetch(`${BASE}/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      })
    } catch (err) {
      console.warn('Logout request failed:', err)
    }
  }

  clearSession()
}

export async function getMe(): Promise<UserInfo> {
  const token = getToken()

  if (!token) {
    throw new Error('Not authenticated')
  }

  const res = await fetch(`${BASE}/me`, {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  })

  if (!res.ok) {
    clearSession()
    throw new Error('Session invalid or expired')
  }

  return res.json()
}
