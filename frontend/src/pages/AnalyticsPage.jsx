import { useEffect, useMemo, useState } from 'react'
import { api, errorMessage } from '../api/client.js'
import { useAuth } from '../context/AuthContext.jsx'

const formatDate = (value) => value
  ? new Intl.DateTimeFormat('tr-TR', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(value))
  : '-'

function MetricCard({ label, value, detail, tone = 'indigo' }) {
  const colors = {
    indigo: 'from-indigo-500/20 to-indigo-500/5 text-indigo-200',
    emerald: 'from-emerald-500/20 to-emerald-500/5 text-emerald-200',
    amber: 'from-amber-500/20 to-amber-500/5 text-amber-200',
    sky: 'from-sky-500/20 to-sky-500/5 text-sky-200',
  }
  return (
    <div className={`rounded-2xl border border-slate-800 bg-gradient-to-br p-5 ${colors[tone]}`}>
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-2 text-3xl font-bold text-white">{value}</p>
      <p className="mt-2 text-xs">{detail}</p>
    </div>
  )
}

function ScoreTrend({ items }) {
  if (!items.length) return <EmptyText text="Trend için henüz tamamlanmış quiz yok." />
  const width = 720
  const height = 230
  const padding = 28
  const x = (index) => items.length === 1 ? width / 2 : padding + (index * (width - padding * 2)) / (items.length - 1)
  const y = (score) => height - padding - (score * (height - padding * 2)) / 100
  const points = items.map((item, index) => `${x(index)},${y(item.percentage)}`).join(' ')
  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} className="h-64 w-full" role="img" aria-label="Quiz başarı trendi">
        {[0, 25, 50, 75, 100].map((score) => (
          <g key={score}>
            <line x1={padding} x2={width - padding} y1={y(score)} y2={y(score)} stroke="#334155" strokeWidth="1" />
            <text x="0" y={y(score) + 4} fill="#64748b" fontSize="11">{score}</text>
          </g>
        ))}
        <polyline points={points} fill="none" stroke="#818cf8" strokeWidth="4" strokeLinejoin="round" strokeLinecap="round" />
        {items.map((item, index) => (
          <g key={item.attempt_id}>
            <circle cx={x(index)} cy={y(item.percentage)} r="6" fill="#0f172a" stroke="#a5b4fc" strokeWidth="3">
              <title>{item.course_title}: %{item.percentage}</title>
            </circle>
            <text x={x(index)} y={height - 6} textAnchor="middle" fill="#64748b" fontSize="10">{index + 1}</text>
          </g>
        ))}
      </svg>
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>Eski denemeler</span><span>Son deneme</span>
      </div>
    </div>
  )
}

function EmptyText({ text }) {
  return <div className="flex min-h-40 items-center justify-center rounded-xl border border-dashed border-slate-700 text-sm text-slate-500">{text}</div>
}

export default function AnalyticsPage({ onNavigate }) {
  const { user, logout } = useAuth()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [courseFilter, setCourseFilter] = useState('all')

  useEffect(() => {
    async function loadAnalytics() {
      setLoading(true)
      setError('')
      try {
        const response = await api.get('/analytics/overview')
        setData(response.data)
      } catch (err) {
        setError(errorMessage(err))
      } finally {
        setLoading(false)
      }
    }
    loadAnalytics()
  }, [])

  const visibleTopics = useMemo(() => {
    if (!data) return []
    if (courseFilter === 'all') return data.topics
    return data.topics.filter((topic) => topic.courses.includes(courseFilter))
  }, [data, courseFilter])

  const weakestTopic = data?.topics.find((topic) => topic.wrong > 0)

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-4">
            <button onClick={() => onNavigate('dashboard')} className="rounded-xl border border-slate-700 px-3 py-2 text-sm hover:bg-slate-800">← Çalışma Alanı</button>
            <div><h1 className="text-xl font-bold">Öğrenme Raporu</h1><p className="text-xs text-slate-500">{user?.email}</p></div>
          </div>
          <button onClick={logout} className="text-sm text-slate-400 hover:text-white">Çıkış</button>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-300">Kişisel Analytics</p>
            <h2 className="mt-2 text-3xl font-bold md:text-4xl">Nerede güçlüsün, nerede tekrar gerek?</h2>
            <p className="mt-3 max-w-2xl text-slate-400">Tüm quiz geçmişin ders ve konu bazında analiz edilir. Yeni bir quiz tamamladığında rapor otomatik güncellenir.</p>
          </div>
          {data && <p className="text-xs text-slate-500">Son hesaplama: {formatDate(data.generated_at)}</p>}
        </div>

        {loading && <div className="card animate-pulse text-slate-400">Rapor hazırlanıyor...</div>}
        {error && <div className="rounded-2xl border border-red-900 bg-red-950/50 p-5 text-red-200">{error}</div>}

        {data && (
          <div className="space-y-6">
            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <MetricCard label="Genel başarı" value={`%${data.summary.accuracy}`} detail={`${data.summary.total_correct}/${data.summary.total_questions} doğru cevap`} tone="emerald" />
              <MetricCard label="Ortalama quiz skoru" value={`%${data.summary.average_score}`} detail={`${data.summary.total_attempts} tamamlanmış quiz`} />
              <MetricCard label="Çalışılan ders" value={data.summary.courses_studied} detail="Quiz çözülen farklı ders" tone="sky" />
              <MetricCard label="Öncelikli konu" value={weakestTopic?.topic || 'Harika!'} detail={weakestTopic ? `${weakestTopic.wrong} yanlış cevap` : 'Belirgin bir zayıflık yok'} tone="amber" />
            </section>

            <section className="grid gap-6 xl:grid-cols-3">
              <div className="card xl:col-span-2">
                <div className="mb-5"><h3 className="text-lg font-bold">Başarı trendi</h3><p className="text-sm text-slate-500">Son 16 quiz denemesi • yüzde skor</p></div>
                <ScoreTrend items={data.trend} />
              </div>
              <div className="card">
                <h3 className="text-lg font-bold">Akıllı tekrar planı</h3>
                <div className="mt-4 space-y-3">
                  {data.recommendations.length ? data.recommendations.map((item, index) => (
                    <div key={item.topic} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                      <div className="flex items-center gap-3"><span className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-500/20 text-xs font-bold text-indigo-300">{index + 1}</span><p className="font-semibold">{item.topic}</p></div>
                      <p className="mt-2 text-sm leading-6 text-slate-400">{item.message}</p>
                    </div>
                  )) : <EmptyText text="Öneri için önce bir quiz tamamla." />}
                </div>
              </div>
            </section>

            <section className="card">
              <div className="mb-5 flex flex-col justify-between gap-3 md:flex-row md:items-center">
                <div><h3 className="text-lg font-bold">Ders performansı</h3><p className="text-sm text-slate-500">Dersler arasında başarı ve aktivite karşılaştırması</p></div>
              </div>
              {data.courses.length ? (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {data.courses.map((course) => (
                    <div key={course.course_id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                      <div className="flex items-start justify-between gap-3"><h4 className="font-semibold">{course.course_title}</h4><span className={`rounded-full px-2 py-1 text-xs ${course.accuracy >= 70 ? 'bg-emerald-500/15 text-emerald-300' : 'bg-amber-500/15 text-amber-300'}`}>%{course.accuracy}</span></div>
                      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-cyan-400" style={{ width: `${course.accuracy}%` }} /></div>
                      <div className="mt-3 flex justify-between text-xs text-slate-500"><span>{course.attempts} quiz</span><span>{course.correct}/{course.total} doğru</span><span>{formatDate(course.last_activity)}</span></div>
                    </div>
                  ))}
                </div>
              ) : <EmptyText text="Henüz ders performans verisi yok." />}
            </section>

            <section className="card">
              <div className="mb-5 flex flex-col justify-between gap-3 md:flex-row md:items-center">
                <div><h3 className="text-lg font-bold">Konu hakimiyeti</h3><p className="text-sm text-slate-500">En çok yanlış yapılan konular önce gösterilir</p></div>
                <select className="input md:w-64" value={courseFilter} onChange={(event) => setCourseFilter(event.target.value)}>
                  <option value="all">Tüm dersler</option>
                  {data.courses.map((course) => <option key={course.course_id} value={course.course_title}>{course.course_title}</option>)}
                </select>
              </div>
              {visibleTopics.length ? (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[720px] text-left text-sm">
                    <thead className="border-b border-slate-800 text-xs uppercase tracking-wider text-slate-500"><tr><th className="pb-3">Konu</th><th className="pb-3">Ders</th><th className="pb-3">Başarı</th><th className="pb-3">Doğru / Yanlış</th><th className="pb-3">Tekrar sayfaları</th></tr></thead>
                    <tbody className="divide-y divide-slate-800">
                      {visibleTopics.map((topic) => (
                        <tr key={topic.topic}><td className="py-4 font-medium">{topic.topic}</td><td className="py-4 text-slate-400">{topic.courses.join(', ')}</td><td className="py-4"><span className={topic.accuracy >= 70 ? 'text-emerald-300' : topic.accuracy >= 50 ? 'text-amber-300' : 'text-red-300'}>%{topic.accuracy}</span></td><td className="py-4"><span className="text-emerald-300">{topic.correct}</span><span className="text-slate-600"> / </span><span className="text-red-300">{topic.wrong}</span></td><td className="py-4 text-slate-400">{topic.pages.length ? topic.pages.join(', ') : '-'}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : <EmptyText text="Bu filtre için konu verisi bulunamadı." />}
            </section>

            <section className="card">
              <div className="mb-5"><h3 className="text-lg font-bold">Son yanlışlar</h3><p className="text-sm text-slate-500">Neyi, hangi derste ve neden yanlış yaptığını tekrar incele</p></div>
              {data.recent_mistakes.length ? (
                <div className="grid gap-4 lg:grid-cols-2">
                  {data.recent_mistakes.map((mistake) => (
                    <article key={mistake.answer_id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                      <div className="flex flex-wrap items-center gap-2 text-xs"><span className="rounded-full bg-red-500/15 px-2 py-1 text-red-300">Yanlış</span><span className="text-indigo-300">{mistake.course_title}</span><span className="text-slate-600">•</span><span className="text-slate-400">{mistake.topic}</span><span className="ml-auto text-slate-600">{formatDate(mistake.completed_at)}</span></div>
                      <p className="mt-3 font-medium leading-6">{mistake.question}</p>
                      <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2"><p className="rounded-lg bg-red-500/10 p-2 text-red-200">Cevabın: {mistake.user_answer || 'Boş'}</p><p className="rounded-lg bg-emerald-500/10 p-2 text-emerald-200">Doğru: {mistake.correct_answer}</p></div>
                      <p className="mt-3 text-sm leading-6 text-slate-400">{mistake.explanation}</p>
                      <p className="mt-2 text-xs text-slate-600">{mistake.document_name}{mistake.source_page ? ` • Sayfa ${mistake.source_page}` : ''}</p>
                    </article>
                  ))}
                </div>
              ) : <EmptyText text="Henüz yanlış cevap kaydı yok. Böyle devam!" />}
            </section>
          </div>
        )}
      </div>
    </main>
  )
}
