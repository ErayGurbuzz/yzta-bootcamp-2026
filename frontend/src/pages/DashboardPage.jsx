import { useEffect, useMemo, useState } from 'react'
import { api, errorMessage } from '../api/client.js'
import { useAuth } from '../context/AuthContext.jsx'
import ChatPanel from '../components/ChatPanel.jsx'
import CourseForm from '../components/CourseForm.jsx'
import DocumentList from '../components/DocumentList.jsx'
import DocumentUpload from '../components/DocumentUpload.jsx'
import QuizPanel from '../components/QuizPanel.jsx'
import StatusMessage from '../components/StatusMessage.jsx'

export default function DashboardPage() {
  const { user, logout } = useAuth()
  const [courses, setCourses] = useState([])
  const [documents, setDocuments] = useState([])
  const [selectedCourse, setSelectedCourse] = useState('')
  const [selectedDoc, setSelectedDoc] = useState('')
  const [courseTitle, setCourseTitle] = useState('Yapay Zekâ')
  const [file, setFile] = useState(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [question, setQuestion] = useState('Bu dokümanın ana fikri nedir?')
  const [chatResult, setChatResult] = useState(null)
  const [mode, setMode] = useState('default')
  const [quiz, setQuiz] = useState(null)
  const [quizAnswers, setQuizAnswers] = useState({})
  const [quizResult, setQuizResult] = useState(null)

  const readyDocuments = useMemo(() => documents.filter((d) => d.status === 'ready'), [documents])

  useEffect(() => {
    refresh()
  }, [])

  async function refresh() {
    const [courseRes, docRes] = await Promise.all([api.get('/courses'), api.get('/documents')])
    setCourses(courseRes.data)
    setDocuments(docRes.data)
    if (!selectedCourse && courseRes.data[0]) setSelectedCourse(String(courseRes.data[0].id))
    if (!selectedDoc && docRes.data.find((d) => d.status === 'ready')) {
      setSelectedDoc(String(docRes.data.find((d) => d.status === 'ready').id))
    }
  }

  async function createCourse(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await api.post('/courses', { title: courseTitle, description: 'StudyMate demo dersi' })
      setMessage('Ders oluşturuldu')
      await refresh()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function uploadDocument(e) {
    e.preventDefault()
    if (!selectedCourse || !file) return
    setLoading(true)
    setError('')
    setMessage('PDF işleniyor. Gerçek Gemini embedding kullanıldığı için birkaç dakika sürebilir.')
    try {
      const form = new FormData()
      form.append('course_id', selectedCourse)
      form.append('file', file)
      await api.post('/documents/upload', form)
      setMessage('PDF yüklendi, chunklandı ve ChromaDB’ye gerçek embedding ile kaydedildi')
      await refresh()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function askQuestion(e) {
    e.preventDefault()
    if (!selectedDoc) return
    setLoading(true)
    setError('')
    setChatResult(null)
    try {
      const res = await api.post('/chat/ask', { document_id: Number(selectedDoc), question, mode, top_k: 5 })
      setChatResult(res.data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function generateQuiz() {
    if (!selectedDoc) return
    setLoading(true)
    setError('')
    setQuiz(null)
    setQuizResult(null)
    setQuizAnswers({})
    try {
      const res = await api.post('/quiz/generate', {
        document_id: Number(selectedDoc),
        question_count: 5,
        difficulty: 'medium',
        question_type: 'mcq',
      })
      setQuiz(res.data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function submitQuiz() {
    if (!quiz) return
    setLoading(true)
    setError('')
    try {
      const answers = Object.entries(quizAnswers).map(([question_id, answer]) => ({
        question_id: Number(question_id),
        answer,
      }))
      const res = await api.post(`/quiz/${quiz.id}/submit`, { answers })
      setQuizResult(res.data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/80">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-2xl font-bold">StudyMate</h1>
            <p className="text-sm text-slate-400">Merhaba, {user?.email}</p>
          </div>
          <button onClick={logout} className="rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800">Çıkış</button>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-8 lg:grid-cols-3">
        <section className="space-y-6 lg:col-span-1">
          <CourseForm
            courseTitle={courseTitle}
            setCourseTitle={setCourseTitle}
            onSubmit={createCourse}
            loading={loading}
          />
          <DocumentUpload
            courses={courses}
            selectedCourse={selectedCourse}
            setSelectedCourse={setSelectedCourse}
            setFile={setFile}
            onSubmit={uploadDocument}
            loading={loading}
            file={file}
          />
          <DocumentList
            documents={documents}
            readyDocuments={readyDocuments}
            selectedDoc={selectedDoc}
            setSelectedDoc={setSelectedDoc}
          />
        </section>

        <section className="space-y-6 lg:col-span-2">
          <StatusMessage message={message} error={error} />
          <ChatPanel
            question={question}
            setQuestion={setQuestion}
            mode={mode}
            setMode={setMode}
            onSubmit={askQuestion}
            loading={loading}
            selectedDoc={selectedDoc}
            chatResult={chatResult}
          />
          <QuizPanel
            quiz={quiz}
            quizAnswers={quizAnswers}
            setQuizAnswers={setQuizAnswers}
            quizResult={quizResult}
            onGenerate={generateQuiz}
            onSubmit={submitQuiz}
            loading={loading}
            selectedDoc={selectedDoc}
          />
        </section>
      </div>
    </main>
  )
}
