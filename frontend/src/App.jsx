import { useAuth } from './context/AuthContext.jsx'
import LoginPage from './pages/LoginPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'

export default function App() {
  const auth = useAuth()
  return auth.isAuthenticated ? <DashboardPage /> : <LoginPage />
}
