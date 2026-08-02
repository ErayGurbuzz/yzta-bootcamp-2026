import { useEffect, useMemo, useState } from 'react'
import { api, errorMessage } from '../api/client.js'

const WEEKDAYS = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz']
const TYPE_META = {
  review: { label: 'Konu tekrarı', color: 'bg-sky-500/15 text-sky-300 border-sky-900' },
  flashcard: { label: 'Flashcard', color: 'bg-violet-500/15 text-violet-300 border-violet-900' },
  quiz: { label: 'Quiz', color: 'bg-amber-500/15 text-amber-300 border-amber-900' },
}

const formatDate = (value, options = {}) => new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'short', ...options }).format(new Date(`${value}T12:00:00`))

export default function StudyPlanPage({ onNavigate }) {
  const [courses, setCourses] = useState([])
  const [selectedCourses, setSelectedCourses] = useState([])
  const [durationDays, setDurationDays] = useState(14)
  const [dailyMinutes, setDailyMinutes] = useState(60)
  const [studyDays, setStudyDays] = useState([0, 1, 2, 3, 4])
  const [scheduleMode, setScheduleMode] = useState('auto')
  const [availability, setAvailability] = useState(WEEKDAYS.map((_, weekday) => ({ weekday, enabled: weekday < 5, start_time: weekday < 5 ? '18:00' : '10:00', end_time: weekday < 5 ? '19:00' : '11:00' })))
  const [goal, setGoal] = useState('Zayıf olduğum konuları güçlendirmek ve quiz başarımı artırmak')
  const [plans, setPlans] = useState([])
  const [activePlan, setActivePlan] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showAllDays, setShowAllDays] = useState(false)

  useEffect(() => {
    async function initialize() {
      try {
        const [courseResponse, planResponse] = await Promise.all([api.get('/courses'), api.get('/study-plans')])
        setCourses(courseResponse.data)
        if (courseResponse.data[0]) setSelectedCourses([courseResponse.data[0].id])
        setPlans(planResponse.data)
        if (planResponse.data[0]) setActivePlan(planResponse.data[0])
      } catch (err) {
        setError(errorMessage(err))
      } finally {
        setLoading(false)
      }
    }
    initialize()
  }, [])

  const visibleDays = useMemo(() => {
    const days = activePlan?.plan_data?.days || []
    return showAllDays ? days : days.slice(0, 7)
  }, [activePlan, showAllDays])

  const today = new Date().toISOString().slice(0, 10)
  const nextTask = useMemo(() => activePlan?.plan_data?.days.flatMap((day) => day.tasks.map((task) => ({ ...task, date: day.date }))).find((task) => !task.completed && task.date >= today), [activePlan, today])

  function toggleDay(day) {
    setStudyDays((items) => items.includes(day) ? items.filter((item) => item !== day) : [...items, day].sort())
    setAvailability((items) => items.map((item) => item.weekday === day ? { ...item, enabled: !item.enabled } : item))
  }

  function updateAvailability(weekday, field, value) {
    setAvailability((items) => items.map((item) => item.weekday === weekday ? { ...item, [field]: value } : item))
  }

  function minutesBetween(start, end) {
    const [startHour, startMinute] = start.split(':').map(Number)
    const [endHour, endMinute] = end.split(':').map(Number)
    return Math.max(15, Math.min(600, (endHour * 60 + endMinute) - (startHour * 60 + startMinute)))
  }

  function availabilityPayload() {
    return availability.filter((item) => item.enabled).map((item) => ({ ...item, minutes: minutesBetween(item.start_time, item.end_time) }))
  }

  async function generatePlan(event) {
    event.preventDefault()
    if (!selectedCourses.length || !studyDays.length) return
    setLoading(true)
    setError('')
    try {
      const response = await api.post('/study-plans/generate', {
        course_ids: selectedCourses,
        duration_days: durationDays,
        daily_minutes: dailyMinutes,
        study_days: studyDays,
        schedule_mode: scheduleMode,
        availability: availabilityPayload(),
        goal,
      })
      setActivePlan(response.data)
      setPlans((items) => [response.data, ...items])
      setShowAllDays(false)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  function openPlan(plan) {
    setActivePlan(plan)
    setShowAllDays(false)
    const data = plan.plan_data
    const courseId = data.focus_areas?.[0]?.course_id
    if (courseId) setSelectedCourses([courseId])
    setDailyMinutes(data.daily_minutes || 60)
    setStudyDays(data.study_days || [0, 1, 2, 3, 4])
    setScheduleMode(data.schedule_mode || 'auto')
    if (data.availability?.length) {
      setAvailability(WEEKDAYS.map((_, weekday) => {
        const saved = data.availability.find((item) => Number(item.weekday) === weekday)
        return saved ? { ...saved, enabled: true } : { weekday, enabled: false, start_time: '18:00', end_time: '19:00' }
      }))
    }
  }

  async function updateActiveSchedule() {
    if (!activePlan || !studyDays.length) return
    setLoading(true)
    setError('')
    try {
      const response = await api.patch(`/study-plans/${activePlan.id}/schedule`, { daily_minutes: dailyMinutes, study_days: studyDays, schedule_mode: scheduleMode, availability: availabilityPayload() })
      setActivePlan(response.data)
      setPlans((items) => items.map((plan) => plan.id === response.data.id ? response.data : plan))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function finishDay(day) {
    if (!activePlan) return
    setLoading(true)
    setError('')
    try {
      const response = await api.post(`/study-plans/${activePlan.id}/finish-day`, { date: day.date })
      setActivePlan(response.data)
      setPlans((items) => items.map((plan) => plan.id === response.data.id ? response.data : plan))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function deletePlan(plan) {
    if (!window.confirm(`“${plan.title}” silinsin mi?`)) return
    setLoading(true)
    try {
      await api.delete(`/study-plans/${plan.id}`)
      const remaining = plans.filter((item) => item.id !== plan.id)
      setPlans(remaining)
      if (activePlan?.id === plan.id) setActivePlan(remaining[0] || null)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function toggleTask(task) {
    if (!activePlan) return
    setError('')
    try {
      const response = await api.patch(`/study-plans/${activePlan.id}/tasks/${task.id}`, { completed: !task.completed })
      setActivePlan(response.data)
      setPlans((items) => items.map((plan) => plan.id === response.data.id ? response.data : plan))
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div><h1 className="text-xl font-bold">Akıllı Çalışma Planı</h1><p className="text-xs text-slate-500">Zayıflıklarına göre kişiselleştirilmiş program</p></div>
          <button onClick={() => onNavigate('dashboard')} className="rounded-xl border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800">← Çalışma Alanı</button>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-6 py-8">
        {error && <div className="mb-5 rounded-xl border border-red-900 bg-red-950/50 p-4 text-red-200">{error}</div>}
        <div className="grid gap-6 xl:grid-cols-4">
          <aside className="space-y-6 xl:col-span-1">
            <form onSubmit={generatePlan} className="card">
              <h2 className="text-lg font-bold">Yeni plan oluştur</h2>
              <p className="mt-1 text-xs leading-5 text-slate-500">Quiz yanlışların ve flashcard ilerlemen otomatik analiz edilir.</p>

              <label className="mt-5 block text-sm font-medium">Dersler</label>
              <select className="input mt-2" value={selectedCourses[0] || ''} onChange={(event) => setSelectedCourses(event.target.value ? [Number(event.target.value)] : [])}>
                {!courses.length && <option value="">Önce bir ders oluşturmalısın</option>}
                {courses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}
              </select>
              <p className="mt-2 text-xs text-slate-500">Her ders için ayrı plan oluşturulur; geçmiş planlar arasında geçiş yapabilirsin.</p>

              <label className="mt-5 block text-sm font-medium">Hedef</label>
              <textarea className="input mt-2 min-h-24 resize-none" value={goal} onChange={(event) => setGoal(event.target.value)} maxLength={500} />

              <div className="mt-5 grid grid-cols-2 gap-3">
                <label className="text-sm">Plan süresi<select className="input mt-2" value={durationDays} onChange={(event) => setDurationDays(Number(event.target.value))}><option value="7">7 gün</option><option value="14">14 gün</option><option value="21">21 gün</option><option value="30">30 gün</option></select></label>
                <label className="text-sm">Günlük süre<select className="input mt-2" value={dailyMinutes} onChange={(event) => setDailyMinutes(Number(event.target.value))}><option value="30">30 dk</option><option value="60">1 saat</option><option value="120">2 saat</option><option value="180">3 saat</option><option value="240">4 saat</option><option value="360">6 saat</option><option value="480">8 saat</option><option value="600">10 saat</option></select></label>
              </div>

              <label className="mt-5 block text-sm font-medium">Gün planlama yöntemi</label>
              <div className="mt-2 grid grid-cols-2 gap-2 rounded-xl bg-slate-950 p-1 text-sm">
                <button type="button" onClick={() => { setScheduleMode('auto'); setStudyDays([0, 1, 2, 3, 4]) }} className={`rounded-lg px-3 py-2 ${scheduleMode === 'auto' ? 'bg-indigo-600' : 'text-slate-400'}`}>Otomatik öner</button>
                <button type="button" onClick={() => setScheduleMode('manual')} className={`rounded-lg px-3 py-2 ${scheduleMode === 'manual' ? 'bg-indigo-600' : 'text-slate-400'}`}>Kendim belirle</button>
              </div>
              {scheduleMode === 'auto' ? <div className="mt-3 rounded-xl border border-indigo-900 bg-indigo-950/30 p-3 text-xs leading-5 text-indigo-200">Hafta içi saat 18:00’dan başlayacak şekilde günlük sürene göre dengeli program önerilecek.</div> : (
                <div className="mt-3 space-y-2">
                  {availability.map((item) => <div key={item.weekday} className={`rounded-xl border p-3 ${item.enabled ? 'border-slate-700 bg-slate-950' : 'border-slate-800 opacity-50'}`}><div className="flex items-center justify-between"><label className="flex items-center gap-2 text-sm font-medium"><input type="checkbox" checked={item.enabled} onChange={() => toggleDay(item.weekday)} className="accent-indigo-500" />{WEEKDAYS[item.weekday]}</label>{item.enabled && <span className="text-xs text-slate-500">{minutesBetween(item.start_time, item.end_time)} dk</span>}</div>{item.enabled && <div className="mt-2 grid grid-cols-2 gap-2"><label className="text-xs text-slate-500">Başlangıç<input className="input mt-1 px-2 py-2" type="time" value={item.start_time} onChange={(event) => updateAvailability(item.weekday, 'start_time', event.target.value)} /></label><label className="text-xs text-slate-500">Bitiş<input className="input mt-1 px-2 py-2" type="time" value={item.end_time} onChange={(event) => updateAvailability(item.weekday, 'end_time', event.target.value)} /></label></div>}</div>)}
                </div>
              )}

              <button className="btn mt-6 w-full" disabled={loading || !selectedCourses.length || !studyDays.length}>{loading ? 'Plan hazırlanıyor...' : 'Kişisel plan oluştur'}</button>
            </form>

            <section className="card">
              <h2 className="font-bold">Geçmiş planlar</h2>
              <div className="mt-3 space-y-2">
                {plans.map((plan) => <div key={plan.id} className={`rounded-xl border p-3 ${activePlan?.id === plan.id ? 'border-indigo-600 bg-indigo-950/40' : 'border-slate-800'}`}><button onClick={() => openPlan(plan)} className="w-full text-left"><p className="text-sm font-medium">{plan.plan_data.focus_areas?.[0]?.course_title || plan.title}</p><p className="mt-1 text-xs text-slate-500">%{plan.plan_data.progress} • {formatDate(plan.plan_data.start_date)}–{formatDate(plan.plan_data.end_date)}</p></button><button onClick={() => deletePlan(plan)} className="mt-2 text-xs text-red-400 hover:text-red-300">Planı sil</button></div>)}
                {!plans.length && <p className="text-sm text-slate-500">Henüz kayıtlı plan yok.</p>}
              </div>
            </section>
          </aside>

          <section className="space-y-6 xl:col-span-3">
            {activePlan ? (
              <>
                <section className="overflow-hidden rounded-2xl border border-indigo-900 bg-gradient-to-br from-indigo-950/70 via-slate-900 to-slate-900 p-6 shadow-xl">
                  <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
                    <div><p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-300">Aktif program</p><h2 className="mt-2 text-2xl font-bold">{activePlan.title}</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">{activePlan.plan_data.goal}</p></div>
                    <div className="min-w-48 rounded-xl bg-slate-950/60 p-4"><div className="flex justify-between text-sm"><span>Genel ilerleme</span><strong>%{activePlan.plan_data.progress}</strong></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-800"><div className="h-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all" style={{ width: `${activePlan.plan_data.progress}%` }} /></div><p className="mt-2 text-xs text-slate-500">{activePlan.plan_data.completed_tasks}/{activePlan.plan_data.total_tasks} görev</p></div>
                  </div>
                  <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4"><Stat label="Çalışma günü" value={activePlan.plan_data.total_study_days} /><Stat label="Günlük hedef" value={`${activePlan.plan_data.daily_minutes} dk`} /><Stat label="Toplam görev" value={activePlan.plan_data.total_tasks} /><Stat label="Bitiş" value={formatDate(activePlan.plan_data.end_date)} /></div>
                </section>

                {activePlan.plan_data.alerts?.length > 0 && <section className="space-y-3">{activePlan.plan_data.alerts.map((alert, index) => <div key={`${alert.type}-${index}`} className={`rounded-xl border p-4 text-sm ${alert.type === 'extension' || alert.type === 'intensity' ? 'border-amber-800 bg-amber-950/30 text-amber-200' : 'border-indigo-800 bg-indigo-950/30 text-indigo-200'}`}><strong className="mr-2">{alert.type === 'extension' ? 'Plan uzadı:' : alert.type === 'intensity' ? 'Yoğunluk uyarısı:' : 'Plan güncellendi:'}</strong>{alert.message}</div>)}</section>}

                <section className="card">
                  <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center"><div><h2 className="text-lg font-bold">Müsaitlik değişti mi?</h2><p className="mt-1 text-sm text-slate-500">Soldaki gün ve saatleri düzenle; kalan görevler yeni kapasiteye göre yeniden dağıtılsın.</p></div><button onClick={updateActiveSchedule} disabled={loading || !studyDays.length} className="rounded-xl border border-indigo-700 px-4 py-3 text-sm font-semibold text-indigo-200 hover:bg-indigo-950 disabled:opacity-40">Aktif planı güncelle</button></div>
                </section>

                {nextTask && <section className="card border-indigo-800"><div className="flex flex-col justify-between gap-4 md:flex-row md:items-center"><div><p className="text-xs font-semibold uppercase tracking-wider text-indigo-300">Sıradaki görev • {formatDate(nextTask.date)}</p><h3 className="mt-2 text-lg font-bold">{nextTask.title}</h3><p className="mt-1 text-sm text-slate-400">{nextTask.course_title} • {nextTask.duration_minutes} dakika</p></div><button onClick={() => toggleTask(nextTask)} className="btn whitespace-nowrap">Tamamlandı olarak işaretle</button></div></section>}

                <section className="card">
                  <div className="mb-5"><h2 className="text-lg font-bold">Plan takvimi</h2><p className="mt-1 text-sm text-slate-500">Tüm programın tarih, saat ve yoğunluk görünümü</p></div>
                  <PlanCalendar days={activePlan.plan_data.days} today={today} />
                </section>

                <section className="card">
                  <h2 className="text-lg font-bold">Öncelikli konular</h2>
                  <p className="mt-1 text-sm text-slate-500">Quiz yanlışları ve bekleyen flashcard’lara göre sıralandı.</p>
                  <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {activePlan.plan_data.focus_areas.slice(0, 6).map((area, index) => <div key={`${area.course_id}-${area.topic}`} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4"><div className="flex justify-between"><span className="text-xs text-indigo-300">#{index + 1} • {area.course_title}</span>{area.accuracy !== null && <span className={area.accuracy < 60 ? 'text-xs text-red-300' : 'text-xs text-emerald-300'}>%{area.accuracy}</span>}</div><p className="mt-2 font-semibold">{area.topic}</p><div className="mt-3 flex gap-3 text-xs text-slate-500"><span>{area.wrong_answers} yanlış</span><span>{area.remaining_flashcards} bekleyen kart</span></div></div>)}
                  </div>
                </section>

                <section>
                  <div className="mb-4 flex items-end justify-between"><div><h2 className="text-xl font-bold">Günlük program</h2><p className="text-sm text-slate-500">Görevleri tamamladıkça plan ilerlemen güncellenir.</p></div></div>
                  <div className="space-y-4">
                    {visibleDays.map((day) => {
                      const completed = day.tasks.filter((task) => task.completed).length
                      return <article key={day.date} className={`card ${day.date === today ? 'border-indigo-600' : ''}`}>
                        <div className="flex flex-col justify-between gap-3 border-b border-slate-800 pb-4 sm:flex-row sm:items-center"><div className="flex items-center gap-3"><span className={`flex h-10 w-10 items-center justify-center rounded-xl font-bold ${day.date === today ? 'bg-indigo-600' : 'bg-slate-800'}`}>{day.day_number}</span><div><h3 className="font-bold">{formatDate(day.date, { weekday: 'long' })}</h3><p className="text-xs text-slate-500">{day.start_time}–{day.end_time} • {day.total_minutes}/{day.capacity_minutes} dk • {completed}/{day.tasks.length} tamamlandı</p></div></div>{day.status === 'finished' ? <span className="rounded-full bg-emerald-500/15 px-3 py-1 text-xs text-emerald-300">Gün kapatıldı ✓</span> : <button onClick={() => finishDay(day)} disabled={loading} className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold hover:bg-emerald-500 disabled:opacity-40">Günü bitir</button>}</div>
                        <div className="mt-4 space-y-3">{day.tasks.map((task) => <Task key={task.id} task={task} onToggle={() => toggleTask(task)} />)}</div>
                      </article>
                    })}
                  </div>
                  {activePlan.plan_data.days.length > 7 && <button onClick={() => setShowAllDays(!showAllDays)} className="mt-4 w-full rounded-xl border border-slate-700 py-3 text-sm font-semibold hover:bg-slate-800">{showAllDays ? 'İlk 7 günü göster' : `Tüm ${activePlan.plan_data.total_study_days} çalışma gününü göster`}</button>}
                </section>
              </>
            ) : <div className="card flex min-h-[500px] flex-col items-center justify-center text-center"><div className="text-6xl">◷</div><h2 className="mt-5 text-2xl font-bold">Kişisel programını oluştur</h2><p className="mt-3 max-w-lg text-slate-400">Derslerini ve uygun günlerini seç. StudyMate geçmiş performansına göre hangi gün hangi konuya çalışacağını planlasın.</p></div>}
          </section>
        </div>
      </div>
    </main>
  )
}

function Stat({ label, value }) {
  return <div className="rounded-xl bg-slate-950/50 p-3"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 font-bold">{value}</p></div>
}

function Task({ task, onToggle }) {
  const meta = TYPE_META[task.type] || TYPE_META.review
  return <div className={`flex gap-3 rounded-xl border p-3 transition ${task.completed ? 'border-emerald-900 bg-emerald-950/20 opacity-70' : 'border-slate-800 bg-slate-950/40'}`}><button onClick={onToggle} className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border ${task.completed ? 'border-emerald-500 bg-emerald-500 text-slate-950' : 'border-slate-600'}`}>{task.completed ? '✓' : ''}</button><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><span className={`rounded-full border px-2 py-0.5 text-xs ${meta.color}`}>{meta.label}</span><span className="text-xs text-slate-500">{task.start_time && `${task.start_time}–${task.end_time} • `}{task.course_title} • {task.duration_minutes} dk</span></div><h4 className={`mt-2 font-semibold ${task.completed ? 'line-through' : ''}`}>{task.title}</h4><p className="mt-1 text-sm leading-6 text-slate-400">{task.description}</p></div></div>
}

function PlanCalendar({ days, today }) {
  if (!days.length) return <p className="text-sm text-slate-500">Takvimde gösterilecek çalışma günü yok.</p>
  const byDate = new Map(days.map((day) => [day.date, day]))
  const firstDate = new Date(`${days[0].date}T12:00:00`)
  const lastDate = new Date(`${days[days.length - 1].date}T12:00:00`)
  const firstWeekday = (firstDate.getDay() + 6) % 7
  const cells = [...Array(firstWeekday).fill(null)]
  for (let cursor = new Date(firstDate); cursor <= lastDate; cursor.setDate(cursor.getDate() + 1)) {
    const date = cursor.toISOString().slice(0, 10)
    cells.push(byDate.get(date) || { date, isRestDay: true })
  }
  while (cells.length % 7) cells.push(null)
  return <div className="overflow-x-auto"><div className="min-w-[760px]"><div className="grid grid-cols-7 gap-2">{WEEKDAYS.map((day) => <div key={day} className="pb-2 text-center text-xs font-semibold uppercase tracking-wider text-slate-500">{day}</div>)}{cells.map((day, index) => day ? day.isRestDay ? <div key={day.date} className="min-h-28 rounded-xl border border-dashed border-slate-800 p-3"><span className="text-xs text-slate-600">{formatDate(day.date)}</span><p className="mt-3 text-xs text-slate-700">Dinlenme</p></div> : <div key={day.date} className={`min-h-28 rounded-xl border p-3 ${day.date === today ? 'border-indigo-500 bg-indigo-950/30' : day.status === 'finished' ? 'border-emerald-900 bg-emerald-950/20' : 'border-slate-800 bg-slate-950/50'}`}><div className="flex justify-between"><span className="text-sm font-bold">{formatDate(day.date)}</span><span className="text-xs text-slate-500">{day.start_time}</span></div><div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800"><div className={`h-full ${day.status === 'finished' ? 'bg-emerald-500' : 'bg-indigo-500'}`} style={{ width: `${day.tasks.length ? day.tasks.filter((task) => task.completed).length * 100 / day.tasks.length : 100}%` }} /></div><p className="mt-2 text-xs text-slate-500">{day.tasks.length} görev • {day.total_minutes} dk</p>{day.status === 'finished' && <p className="mt-1 text-xs text-emerald-300">Tamamlandı</p>}</div> : <div key={`empty-${index}`} className="min-h-28 rounded-xl border border-dashed border-slate-900" />)}</div></div></div>
}
