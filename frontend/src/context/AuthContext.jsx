import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem('studymate_token'))
  const [user, setUser] = useState(null)

  useEffect(() => {
    if (!token) return
    api.get('/auth/me')
      .then((res) => setUser(res.data))
      .catch(() => logout())
  }, [token])

  async function login(email, password) {
    const res = await api.post('/auth/login', { email, password })
    localStorage.setItem('studymate_token', res.data.access_token)
    setToken(res.data.access_token)
    const me = await api.get('/auth/me')
    setUser(me.data)
  }

  async function register(email, password) {
    await api.post('/auth/register', { email, password })
    await login(email, password)
  }

  function logout() {
    localStorage.removeItem('studymate_token')
    setToken(null)
    setUser(null)
  }

  const value = useMemo(() => ({ token, user, login, register, logout, isAuthenticated: Boolean(token) }), [token, user])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
