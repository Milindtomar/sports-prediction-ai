import { MotionConfig } from 'framer-motion'
import { Suspense, lazy, useEffect } from 'react'
import { Navigate, Outlet, Route, Routes, useParams } from 'react-router-dom'
import { Footer, AppHeader } from './components/Shell'
import { Loading } from './components/ui'
import { MatchProvider } from './lib/MatchContext'
import { SPORTS, Sport } from './lib/types'

const Landing = lazy(() => import('./pages/Landing'))
const SportSelect = lazy(() => import('./pages/SportSelect'))
const MatchCenter = lazy(() => import('./pages/MatchCenter'))
const AIAnalytics = lazy(() => import('./pages/AIAnalytics'))
const SimulationLab = lazy(() => import('./pages/SimulationLab'))
const PlayerLab = lazy(() => import('./pages/PlayerLab'))
const ModelInsights = lazy(() => import('./pages/ModelInsights'))
const HciStudy = lazy(() => import('./pages/HciStudy'))

export const lastSport = (): Sport => {
  try { const v = localStorage.getItem('sportsai.sport'); if (v && (SPORTS as readonly string[]).includes(v)) return v as Sport } catch { /* storage unavailable */ }
  return 'cricket'
}

function SportLayout() {
  const { sport } = useParams()
  const ok = (SPORTS as readonly string[]).includes(sport ?? '')
  useEffect(() => {
    if (!ok) return
    document.documentElement.dataset.sport = sport
    try { localStorage.setItem('sportsai.sport', sport!) } catch { /* ignore */ }
  }, [sport, ok])
  if (!ok) return <Navigate to="/sports" replace />
  return (
    <MatchProvider sport={sport as Sport}>
      <AppHeader sport={sport as Sport} />
      <main className="mx-auto max-w-[1500px] px-4 py-4"><Outlet /></main>
      <Footer />
    </MatchProvider>
  )
}

function Plain({ children }: { children: React.ReactNode }) {
  const sport = lastSport()
  useEffect(() => { document.documentElement.dataset.sport = sport }, [sport])
  return <><AppHeader sport={sport} /><main className="mx-auto max-w-[1500px] px-4 py-4">{children}</main><Footer /></>
}

export default function App() {
  return (
    <MotionConfig reducedMotion="user">
      <Suspense fallback={<div className="p-8"><Loading /></div>}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/sports" element={<SportSelect />} />
          <Route path="/app/:sport" element={<SportLayout />}>
            <Route index element={<Navigate to="match" replace />} />
            <Route path="match" element={<MatchCenter />} />
            <Route path="analytics" element={<AIAnalytics />} />
            <Route path="simulate" element={<SimulationLab />} />
            <Route path="players" element={<PlayerLab />} />
          </Route>
          <Route path="/models" element={<Plain><ModelInsights /></Plain>} />
          <Route path="/hci" element={<Plain><HciStudy /></Plain>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </MotionConfig>
  )
}
