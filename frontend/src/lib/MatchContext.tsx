import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { api } from './api'
import { Async, useAsync, useDebounced } from './hooks'
import type { Analysis, MatchCard, MatchDetail, Series, Sport, SportMeta } from './types'

export interface MatchCtx {
  sport: Sport
  meta: Async<SportMeta>
  matches: Async<MatchCard[]>
  matchId: number | null
  selectMatch: (id: number) => void
  match: Async<MatchDetail>
  series: Async<Series>
  step: number
  setStep: (k: number) => void
  playing: boolean
  setPlaying: (p: boolean) => void
  analysis: Async<Analysis>
  targetClass: number | undefined
  setTargetClass: (c: number | undefined) => void
  /** current raw state (from the timeline), the input of simulation / coach / what-if */
  state: Record<string, any> | null
}

const Ctx = createContext<MatchCtx | null>(null)
export const useMatch = () => {
  const c = useContext(Ctx)
  if (!c) throw new Error('useMatch must be used inside <MatchProvider>')
  return c
}

export function MatchProvider({ sport, children }: { sport: Sport; children: React.ReactNode }) {
  const meta = useAsync(() => api.meta(sport), [sport])
  const matches = useAsync(() => api.matches(sport), [sport])
  const [matchId, setMatchId] = useState<number | null>(null)
  const [step, setStepRaw] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [targetClass, setTargetClass] = useState<number | undefined>(undefined)

  useEffect(() => { setMatchId(null); setStepRaw(0); setPlaying(false); setTargetClass(undefined) }, [sport])
  useEffect(() => { if (matchId == null && matches.data?.length) setMatchId(matches.data[0].id) }, [matches.data, matchId])

  const match = useAsync(() => api.match(matchId!), [matchId], matchId != null)
  const series = useAsync(() => api.series(matchId!), [matchId], matchId != null)
  const n = match.data?.timeline.length ?? 0

  // Start each match at a decisive moment (about 60% in) so the first screen already shows something to explain.
  useEffect(() => { if (n) setStepRaw(Math.max(0, Math.floor(n * 0.6))) }, [matchId, n])
  const setStep = (k: number) => setStepRaw(Math.min(Math.max(0, k), Math.max(n - 1, 0)))

  useEffect(() => {
    if (!playing || !n) return
    if (step >= n - 1) { setPlaying(false); return }
    const t = setTimeout(() => setStepRaw((s) => Math.min(s + 1, n - 1)), 1100)
    return () => clearTimeout(t)
  }, [playing, step, n])

  const dStep = useDebounced(step, 140)
  const analysis = useAsync(() => api.step(matchId!, dStep, targetClass), [matchId, dStep, targetClass], matchId != null && n > 0)
  const state = match.data?.timeline[step] ?? null
  const cleaned = useMemo(() => { if (!state) return null; const { step_label, ...rest } = state; return rest }, [state])

  const value: MatchCtx = { sport, meta, matches, matchId, selectMatch: (id) => { setPlaying(false); setMatchId(id) }, match, series, step, setStep, playing, setPlaying, analysis, targetClass, setTargetClass, state: cleaned }
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
