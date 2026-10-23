import type * as T from './types'

const BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? ''

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public detail?: unknown) { super(message) }
}

async function req<R>(path: string, init?: RequestInit): Promise<R> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, { headers: { 'Content-Type': 'application/json' }, ...init })
  } catch {
    throw new ApiError(0, 'network', 'Cannot reach the SPORTS AI server. Check that the backend is running and try again.')
  }
  const text = await res.text()
  let body: any = null
  try { body = text ? JSON.parse(text) : null } catch { /* non-JSON error page */ }
  if (!res.ok) {
    const e = body?.error
    if (res.status === 429) throw new ApiError(429, 'rate_limited', 'Too many requests. Wait a few seconds and retry.')
    throw new ApiError(res.status, e?.code ?? 'http_error', e?.message ?? `Request failed (${res.status})`, e?.detail)
  }
  return body as R
}
const post = <R>(path: string, body: unknown) => req<R>(path, { method: 'POST', body: JSON.stringify(body) })

export const api = {
  health: () => req<{ status: string; models_loaded: boolean }>('/api/health'),
  sports: () => req<{ key: T.Sport; name: string; tagline: string; status: string; analytics: string[]; model: { name: string; accuracy: number; roc_auc: number } | null }[]>('/api/sports'),
  meta: (s: T.Sport) => req<T.SportMeta>(`/api/sports/${s}/meta`),
  defaultState: (s: T.Sport) => req<Record<string, any>>(`/api/sports/${s}/default-state`),
  models: () => req<{ meta: any; sports: Record<string, any>; players: Record<string, any> }>('/api/models'),
  matches: (s?: T.Sport) => req<T.MatchCard[]>(`/api/matches${s ? `?sport=${s}` : ''}`),
  match: (id: number) => req<T.MatchDetail>(`/api/matches/${id}`),
  series: (id: number) => req<T.Series>(`/api/matches/${id}/series`),
  step: (id: number, k: number, cls?: number) => req<T.Analysis>(`/api/matches/${id}/steps/${k}${cls != null ? `?target_class=${cls}` : ''}`),
  predict: (s: T.Sport, state: Record<string, any>, cls?: number) => post<T.Analysis>(`/api/${s}/predict`, { state, target_class: cls ?? null }),
  simulate: (s: T.Sport, state: Record<string, any>, events: { id: string; count?: number }[], overrides: Record<string, any> = {}, sessionId?: number) =>
    post<T.SimResult>(`/api/${s}/simulate`, { state, events, overrides, session_id: sessionId ?? null }),
  sweep: (s: T.Sport, state: Record<string, any>) => post<T.Sweep>(`/api/${s}/simulate/sweep`, { state }),
  coach: (s: T.Sport, state: Record<string, any>, side?: string) => post<T.Coach>(`/api/${s}/coach`, { state, side: side ?? null }),
  players: (s: T.Sport, team?: string) => req<T.PlayerRow[]>(`/api/players?sport=${s}${team ? `&team=${encodeURIComponent(team)}` : ''}`),
  player: (id: number) => req<T.PlayerDetail>(`/api/players/${id}`),
  playerPredict: (id: number, ctx: Record<string, any>) => post<T.PlayerNext>(`/api/players/${id}/predict`, ctx),
  compare: (a: number, b: number) => post<any>('/api/players/compare', { a, b }),
  hciTasks: () => req<{ tasks: T.HciTask[]; sus_items: string[]; trust_items: string[]; consent_text: string; conditions: Record<string, string> }>('/api/hci/tasks'),
  hciCreate: (participant: string, experience: string, consent: boolean, condition?: 'A' | 'B') => post<{ id: number; condition: 'A' | 'B' }>('/api/hci/sessions', { participant, experience, consent, condition: condition ?? null }),
  hciResult: (sid: number, r: Record<string, any>) => post<{ correct: boolean }>(`/api/hci/sessions/${sid}/results`, r),
  hciSus: (sid: number, answers: number[], trust_items?: number[], feedback = '') => post<{ sus_score: number }>(`/api/hci/sessions/${sid}/sus`, { answers, trust_items: trust_items ?? null, feedback }),
  hciResults: () => req<any>('/api/hci/results'),
  hciExportUrl: () => `${BASE}/api/hci/export.csv`,
  hciExportJsonUrl: () => `${BASE}/api/hci/export.json`,
}
