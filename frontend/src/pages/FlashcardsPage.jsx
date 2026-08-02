import { useEffect, useMemo, useState } from 'react'
import { api, errorMessage } from '../api/client.js'

export default function FlashcardsPage({ onNavigate }) {
  const [courses, setCourses] = useState([])
  const [documents, setDocuments] = useState([])
  const [courseId, setCourseId] = useState('')
  const [documentId, setDocumentId] = useState('')
  const [collection, setCollection] = useState({ cards: [], total: 0, learned: 0, remaining: 0 })
  const [currentIndex, setCurrentIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [cardCount, setCardCount] = useState(10)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [studyMode, setStudyMode] = useState('remaining')
  const [topicFilter, setTopicFilter] = useState('all')
  const [shuffleSeed, setShuffleSeed] = useState(0)

  const filteredDocuments = useMemo(() => documents.filter((document) => String(document.course_id) === courseId), [documents, courseId])
  const topics = useMemo(() => [...new Set(collection.cards.map((card) => card.topic))].sort((a, b) => a.localeCompare(b, 'tr')), [collection.cards])
  const learnedTopics = useMemo(() => topics.map((topic) => {
    const cards = collection.cards.filter((card) => card.topic === topic)
    const learnedCards = cards.filter((card) => card.is_learned)
    return { topic, total: cards.length, learned: learnedCards.length, cards: learnedCards }
  }).filter((item) => item.learned > 0).sort((a, b) => b.learned - a.learned), [collection.cards, topics])
  const studyCards = useMemo(() => {
    let cards = studyMode === 'remaining' ? collection.cards.filter((card) => !card.is_learned) : [...collection.cards]
    if (topicFilter !== 'all') cards = cards.filter((card) => card.topic === topicFilter)
    if (shuffleSeed) cards = [...cards].sort((a, b) => ((a.id * 9301 + shuffleSeed) % 49297) - ((b.id * 9301 + shuffleSeed) % 49297))
    return cards
  }, [collection.cards, studyMode, topicFilter, shuffleSeed])
  const currentCard = studyCards[currentIndex] || null
  const progress = collection.total ? Math.round((collection.learned / collection.total) * 100) : 0

  useEffect(() => {
    async function initialize() {
      try {
        const [courseResponse, documentResponse] = await Promise.all([api.get('/courses'), api.get('/documents')])
        const ready = documentResponse.data.filter((document) => document.status === 'ready')
        setCourses(courseResponse.data)
        setDocuments(ready)
        const firstCourse = courseResponse.data.find((course) => ready.some((document) => document.course_id === course.id))
        if (firstCourse) setCourseId(String(firstCourse.id))
      } catch (err) {
        setError(errorMessage(err))
      } finally {
        setLoading(false)
      }
    }
    initialize()
  }, [])

  useEffect(() => {
    const firstDocument = filteredDocuments[0]
    setDocumentId(firstDocument ? String(firstDocument.id) : '')
  }, [courseId, filteredDocuments])

  useEffect(() => {
    if (!documentId) {
      setCollection({ cards: [], total: 0, learned: 0, remaining: 0 })
      return
    }
    loadCards(documentId)
  }, [documentId])

  async function loadCards(id) {
    setLoading(true)
    setError('')
    try {
      const response = await api.get('/flashcards', { params: { document_id: Number(id) } })
      setCollection(response.data)
      setCurrentIndex(0)
      setFlipped(false)
      setTopicFilter('all')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function generateCards() {
    if (!documentId) return
    setLoading(true)
    setError('')
    setMessage('Flashcard’lar ders notlarından hazırlanıyor...')
    try {
      const response = await api.post('/flashcards/generate', { document_id: Number(documentId), card_count: cardCount })
      setCollection(response.data)
      setCurrentIndex(0)
      setFlipped(false)
      setMessage(`${cardCount} kartlık yeni çalışma seti hazır.`)
    } catch (err) {
      setError(errorMessage(err))
      setMessage('')
    } finally {
      setLoading(false)
    }
  }

  async function updateCard(card, isLearned) {
    if (!card) return
    setLoading(true)
    setError('')
    try {
      const response = await api.patch(`/flashcards/${card.id}/review`, { is_learned: isLearned })
      const cards = collection.cards.map((item) => item.id === card.id ? response.data : item)
      const learned = cards.filter((card) => card.is_learned).length
      setCollection({ cards, total: cards.length, learned, remaining: cards.length - learned })
      setFlipped(false)
      setCurrentIndex((index) => {
        const nextLength = studyMode === 'remaining' ? cards.filter((item) => !item.is_learned && (topicFilter === 'all' || item.topic === topicFilter)).length : cards.filter((item) => topicFilter === 'all' || item.topic === topicFilter).length
        return nextLength ? index % nextLength : 0
      })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function reopenTopic(topic) {
    const learnedCards = collection.cards.filter((card) => card.topic === topic && card.is_learned)
    setLoading(true)
    setError('')
    try {
      const responses = await Promise.all(learnedCards.map((card) => api.patch(`/flashcards/${card.id}/review`, { is_learned: false })))
      const reopened = new Map(responses.map((response) => [response.data.id, response.data]))
      const cards = collection.cards.map((card) => reopened.get(card.id) || card)
      const learned = cards.filter((card) => card.is_learned).length
      setCollection({ cards, total: cards.length, learned, remaining: cards.length - learned })
      setStudyMode('remaining')
      setTopicFilter(topic)
      setCurrentIndex(0)
      setMessage(`${topic} kartları tekrar kuyruğuna alındı.`)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  function move(direction) {
    if (!studyCards.length) return
    setCurrentIndex((index) => (index + direction + studyCards.length) % studyCards.length)
    setFlipped(false)
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/80">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div><h1 className="text-xl font-bold">Flashcard Studio</h1><p className="text-xs text-slate-500">Aktif hatırlama ile hızlı tekrar</p></div>
          <button onClick={() => onNavigate('dashboard')} className="rounded-xl border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800">← Çalışma Alanı</button>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-8 lg:grid-cols-3">
        <aside className="space-y-6">
          <section className="card">
            <h2 className="text-lg font-bold">Çalışma seti</h2>
            <label className="mt-4 block text-sm text-slate-400">1. Ders seç</label>
            <select className="input mt-2" value={courseId} onChange={(event) => setCourseId(event.target.value)}>
              {!courses.length && <option value="">Ders bulunamadı</option>}
              {courses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}
            </select>
            <label className="mt-4 block text-sm text-slate-400">2. Kaynak seç</label>
            <select className="input mt-2" value={documentId} onChange={(event) => setDocumentId(event.target.value)}>
              {!filteredDocuments.length && <option value="">Bu derste hazır kaynak yok</option>}
              {filteredDocuments.map((document) => <option key={document.id} value={document.id}>{document.original_filename}</option>)}
            </select>
            <label className="mt-4 block text-sm text-slate-400">Yeni kart sayısı: {cardCount}</label>
            <input className="mt-3 w-full accent-indigo-500" type="range" min="5" max="20" step="5" value={cardCount} onChange={(event) => setCardCount(Number(event.target.value))} />
            <button onClick={generateCards} disabled={loading || !documentId} className="btn mt-5 w-full">Yeni kartlar üret</button>
            <p className="mt-3 text-xs leading-5 text-slate-500">Yeni üretim mevcut kartlarını silmez; aynı dokümanın koleksiyonuna ekler.</p>
          </section>

          <section className="card">
            <div className="flex items-end justify-between"><div><p className="text-sm text-slate-400">Öğrenme ilerlemesi</p><p className="mt-1 text-3xl font-bold">%{progress}</p></div><p className="text-sm text-slate-400">{collection.learned}/{collection.total}</p></div>
            <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all" style={{ width: `${progress}%` }} /></div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-center text-sm"><div className="rounded-xl bg-emerald-500/10 p-3 text-emerald-300"><strong className="block text-xl">{collection.learned}</strong>Öğrenildi</div><div className="rounded-xl bg-amber-500/10 p-3 text-amber-300"><strong className="block text-xl">{collection.remaining}</strong>Tekrar</div></div>
          </section>

          <section className="card">
            <h2 className="text-lg font-bold">Çalışma seçenekleri</h2>
            <div className="mt-4 grid grid-cols-2 gap-2 rounded-xl bg-slate-950 p-1 text-sm">
              <button onClick={() => { setStudyMode('remaining'); setCurrentIndex(0); setFlipped(false) }} className={`rounded-lg px-3 py-2 ${studyMode === 'remaining' ? 'bg-indigo-600 text-white' : 'text-slate-400'}`}>Tekrar kuyruğu</button>
              <button onClick={() => { setStudyMode('all'); setCurrentIndex(0); setFlipped(false) }} className={`rounded-lg px-3 py-2 ${studyMode === 'all' ? 'bg-indigo-600 text-white' : 'text-slate-400'}`}>Tüm kartlar</button>
            </div>
            <label className="mt-4 block text-sm text-slate-400">Konu filtresi</label>
            <select className="input mt-2" value={topicFilter} onChange={(event) => { setTopicFilter(event.target.value); setCurrentIndex(0); setFlipped(false) }}>
              <option value="all">Tüm konular</option>
              {topics.map((topic) => <option key={topic} value={topic}>{topic}</option>)}
            </select>
            <button onClick={() => { setShuffleSeed(Date.now()); setCurrentIndex(0); setFlipped(false) }} disabled={!collection.total} className="mt-3 w-full rounded-xl border border-slate-700 px-4 py-3 text-sm font-semibold hover:bg-slate-800 disabled:opacity-40">Kartları karıştır</button>
          </section>
        </aside>

        <section className="lg:col-span-2">
          {error && <div className="mb-4 rounded-xl border border-red-900 bg-red-950/50 p-4 text-red-200">{error}</div>}
          {message && <div className="mb-4 rounded-xl border border-indigo-800 bg-indigo-950/40 p-4 text-indigo-200">{message}</div>}
          {loading && !currentCard ? <div className="card animate-pulse text-slate-400">Kartlar yükleniyor...</div> : currentCard ? (
            <div>
              <div className="mb-4 flex items-center justify-between text-sm text-slate-500"><span>{currentIndex + 1} / {studyCards.length}</span><span>{currentCard.topic}{currentCard.source_page ? ` • Sayfa ${currentCard.source_page}` : ''}</span></div>
              <button onClick={() => setFlipped(!flipped)} className="group flex min-h-[420px] w-full flex-col items-center justify-center rounded-3xl border border-slate-700 bg-gradient-to-br from-slate-900 to-indigo-950/50 p-8 text-center shadow-2xl shadow-indigo-950/30 transition hover:border-indigo-500">
                <span className="mb-8 rounded-full bg-indigo-500/15 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-indigo-300">{flipped ? 'Cevap' : 'Soru'}</span>
                <p className="max-w-2xl text-2xl font-semibold leading-relaxed md:text-3xl">{flipped ? currentCard.back : currentCard.front}</p>
                <span className="mt-10 text-sm text-slate-500">Kartı çevirmek için tıkla</span>
              </button>
              <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <button onClick={() => move(-1)} className="rounded-xl border border-slate-700 px-4 py-3 hover:bg-slate-800">← Önceki</button>
                <button onClick={() => updateCard(currentCard, false)} disabled={loading || !flipped} className="rounded-xl bg-amber-600 px-4 py-3 font-semibold disabled:opacity-40">Tekrar et</button>
                <button onClick={() => updateCard(currentCard, true)} disabled={loading || !flipped} className="rounded-xl bg-emerald-600 px-4 py-3 font-semibold disabled:opacity-40">Öğrendim</button>
                <button onClick={() => move(1)} className="rounded-xl border border-slate-700 px-4 py-3 hover:bg-slate-800">Sonraki →</button>
              </div>
            </div>
          ) : (
            <div className="card flex min-h-[420px] flex-col items-center justify-center text-center"><div className="text-5xl">◫</div><h2 className="mt-5 text-2xl font-bold">{collection.total ? 'Bu görünümde kart kalmadı' : 'İlk kart setini oluştur'}</h2><p className="mt-3 max-w-md text-slate-400">{collection.total ? 'Başka bir konu seçebilir, tüm kartları açabilir veya öğrenilen bir konuyu tekrar kuyruğuna alabilirsin.' : 'Önce dersini, sonra o derse ait hazır bir kaynağı seç ve çalışma kartlarını oluştur.'}</p></div>
          )}

          <section className="card mt-6">
            <div className="flex items-center justify-between"><div><h2 className="text-lg font-bold">Öğrenilen Konular</h2><p className="mt-1 text-sm text-slate-500">Öğrendiğin kartlar burada konu bazında kalıcı olarak saklanır.</p></div><span className="rounded-full bg-emerald-500/15 px-3 py-1 text-sm font-semibold text-emerald-300">{learnedTopics.length} konu</span></div>
            {learnedTopics.length ? (
              <div className="mt-5 grid gap-3 md:grid-cols-2">
                {learnedTopics.map((item) => (
                  <div key={item.topic} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                    <div className="flex items-start justify-between gap-3"><div><h3 className="font-semibold">{item.topic}</h3><p className="mt-1 text-xs text-slate-500">{item.learned}/{item.total} kart öğrenildi</p></div><span className="text-emerald-400">✓</span></div>
                    <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800"><div className="h-full bg-emerald-500" style={{ width: `${Math.round(item.learned * 100 / item.total)}%` }} /></div>
                    <button onClick={() => reopenTopic(item.topic)} disabled={loading} className="mt-4 text-sm font-semibold text-indigo-300 hover:text-indigo-200 disabled:opacity-40">Konuyu tekrar kuyruğuna al →</button>
                  </div>
                ))}
              </div>
            ) : <div className="mt-5 rounded-xl border border-dashed border-slate-700 p-8 text-center text-sm text-slate-500">Bir karta “Öğrendim” dediğinde konusu burada görünecek.</div>}
          </section>
        </section>
      </div>
    </main>
  )
}
