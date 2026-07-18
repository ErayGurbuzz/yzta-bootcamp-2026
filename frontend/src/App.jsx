import { useState } from 'react'
import { useAuth } from './context/AuthContext.jsx'
import LoginPage from './pages/LoginPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import AnalyticsPage from './pages/AnalyticsPage.jsx'
import FlashcardsPage from './pages/FlashcardsPage.jsx'
import StudyPlanPage from './pages/StudyPlanPage.jsx'

export default function App() {
  const auth = useAuth()
  const [page, setPage] = useState('dashboard')

  if (!auth.isAuthenticated) return <LoginPage />
  if (page === 'analytics') return <AnalyticsPage onNavigate={setPage} />
  if (page === 'flashcards') return <FlashcardsPage onNavigate={setPage} />
  if (page === 'study-plan') return <StudyPlanPage onNavigate={setPage} />
  return <DashboardPage onNavigate={setPage} />
}
