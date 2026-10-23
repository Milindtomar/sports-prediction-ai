export const pct = (p: number, d = 0) => `${(p * 100).toFixed(d)}%`
export const pp = (v: number, d = 1) => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(d)} pp`
export const signed = (v: number, d = 1) => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(d)}`
export const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))
export const cn = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(' ')
export const sportLabel: Record<string, string> = { cricket: 'Cricket', football: 'Football', basketball: 'Basketball' }
export const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Unexpected error')
