import { useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { errorMessage } from '../api/client.js'

export default function LoginPage() {
  const { login, register } = useAuth()
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
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
              <div>
                <input
                  className="input"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="E-posta"
                  autoComplete="email"
                  required
                  aria-describedby={mode === 'register' ? 'email-requirement' : undefined}
                />
                {mode === 'register' && (
                  <p id="email-requirement" className="mt-2 text-xs text-slate-400">
                    Geçerli bir e-posta adresi girin (ör. ad@domain.com).
                  </p>
                )}
              </div>
              <div>
                <input
                  className="input"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Şifre"
                  autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
                  minLength={mode === 'register' ? 8 : undefined}
                  pattern={mode === 'register' ? '(?=.*[a-zçğıöşü])(?=.*[A-ZÇĞİÖŞÜ])(?=.*[^A-Za-zÇĞİÖŞÜçğıöşü0-9\\s]).{8,}' : undefined}
                  title={mode === 'register' ? 'En az 8 karakter, bir büyük harf, bir küçük harf ve bir özel karakter kullanın.' : undefined}
                  required
                  aria-describedby={mode === 'register' ? 'password-requirement' : undefined}
                />
                {mode === 'register' && (
                  <div id="password-requirement" className="mt-2 text-xs text-slate-400">
                    <p>Şifreniz şunları içermelidir:</p>
                    <ul className="mt-1 list-inside list-disc space-y-1">
                      <li>En az 8 karakter</li>
                      <li>En az bir büyük harf</li>
                      <li>En az bir küçük harf</li>
                      <li>En az bir özel karakter (ör. !, ?, @, #)</li>
                    </ul>
                  </div>
                )}
              </div>
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
