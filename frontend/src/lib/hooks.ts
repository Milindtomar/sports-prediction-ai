import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from './api'

export interface Async<T> { data: T | null; error: ApiError | Error | null; loading: boolean; reload: () => void }

/** Runs `fn` whenever `deps` change; stale responses are ignored. Keeps previous data while reloading. */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[], enabled = true): Async<T> {
  const [state, setState] = useState<{ data: T | null; error: Error | null; loading: boolean }>({ data: null, error: null, loading: enabled })
  const tick = useRef(0)
  const [nonce, setNonce] = useState(0)
  useEffect(() => {
    if (!enabled) return
    const id = ++tick.current
    setState((s) => ({ ...s, loading: true, error: null }))
    fn().then(
      (data) => { if (id === tick.current) setState({ data, error: null, loading: false }) },
      (error) => { if (id === tick.current) setState((s) => ({ data: s.data, error, loading: false })) },
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce, enabled])
  const reload = useCallback(() => setNonce((n) => n + 1), [])
  return { ...state, reload }
}

export function useDebounced<T>(value: T, ms = 220): T {
  const [v, setV] = useState(value)
  useEffect(() => { const t = setTimeout(() => setV(value), ms); return () => clearTimeout(t) }, [value, ms])
  return v
}

export function usePersisted<T>(key: string, initial: T): [T, (v: T) => void] {
  const [v, setV] = useState<T>(() => {
    try { const s = localStorage.getItem(key); return s ? (JSON.parse(s) as T) : initial } catch { return initial }
  })
  const set = (x: T) => { setV(x); try { localStorage.setItem(key, JSON.stringify(x)) } catch { /* private mode */ } }
  return [v, set]
}
