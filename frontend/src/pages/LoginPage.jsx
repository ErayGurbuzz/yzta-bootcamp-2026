import { useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { errorMessage } from '../api/client.js'

export default function LoginPage() {
  const { login, register } = useAuth()
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('demo@studymate.local')
  const [password, setPassword] = useState('123456')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      if (mode === 'login') await login(email, password)
      else await register(email, password)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950 text-slate-100">
      <section className="mx-auto flex min-h-screen max-w-6xl items-center justify-center px-6">
        <div className="grid w-full gap-8 lg:grid-cols-2">
          <div className="flex flex-col justify-center">
            <p className="mb-4 inline-flex w-fit rounded-full bg-indigo-500/10 px-4 py-2 text-sm text-indigo-200">RAG + Quiz + Learning Analytics</p>
            <h1 className="text-5xl font-bold tracking-tight">StudyMate</h1>
            <p className="mt-6 max-w-xl text-lg text-slate-300">
              Kendi ders PDF'lerinden kaynaklı cevaplar al, quiz oluştur ve yanlışlarına göre kişisel tekrar önerisi gör.
            </p>
          </div>
          <form onSubmit={submit} className="card">
            <h2 className="text-2xl font-bold">{mode === 'login' ? 'Giriş Yap' : 'Kayıt Ol'}</h2>
            <div className="mt-6 space-y-4">
              <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="E-posta" />
              <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Şifre" />
              {error && <div className="rounded-xl border border-red-900 bg-red-950/60 p-3 text-sm text-red-200">{error}</div>}
              <button className="btn w-full" disabled={loading}>{loading ? 'İşleniyor...' : mode === 'login' ? 'Giriş Yap' : 'Kayıt Ol'}</button>
            </div>
            <button type="button" className="mt-4 text-sm text-indigo-300" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
              {mode === 'login' ? 'Hesabın yok mu? Kayıt ol' : 'Zaten hesabın var mı? Giriş yap'}
            </button>
          </form>
        </div>
      </section>
    </main>
  )
}
