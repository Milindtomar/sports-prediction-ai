import { Bot } from 'lucide-react'
import { useState } from 'react'
import { api } from '../../lib/api'
import { useAsync } from '../../lib/hooks'
import type { Coach, Sport } from '../../lib/types'
import { pct } from '../../lib/format'
import { Disclaimer, ErrorState, Loading, Pill, Segmented } from '../ui'

export function CoachCard({ sport, state, teams }: { sport: Sport; state: Record<string, any> | null; teams?: [string, string] }) {
  const [side, setSide] = useState<'home' | 'away'>('home')
  const key = JSON.stringify(state)
  const c = useAsync<Coach>(() => api.coach(sport, state!, sport === 'cricket' ? 'focus' : side), [sport, key, side], !!state)
  const d = c.data
  const money = (v: number) => (d?.metric === 'expected points' ? `${v.toFixed(2)} pts` : pct(v, 1))
  return (
    <div className="rounded-lg border hairline bg-ink-900 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 text-sm font-semibold"><Bot className="h-4 w-4 text-accent" aria-hidden /> AI Coach</h3>
        <div className="flex items-center gap-2"><Pill tone="model">AI-assisted recommendation</Pill>
          {sport !== 'cricket' && teams && <Segmented label="Coach perspective" value={side} onChange={setSide} options={[{ value: 'home', label: teams[0] }, { value: 'away', label: teams[1] }]} />}</div>
      </div>
      {c.error && <div className="mt-3"><ErrorState error={c.error} onRetry={c.reload} title="Coach unavailable" /></div>}
      {!c.error && !d && <Loading label="Running roll-outs" />}
      {d && !d.available && <p className="mt-3 text-sm text-fog-500">{d.reason}</p>}
      {d && d.available && (
        <div className={c.loading ? 'opacity-60 transition-opacity' : 'transition-opacity'}>
          <p className="mt-3 text-sm text-fog-300"><span className="text-fog-500">Current situation: </span>{d.situation}</p>
          <div className="mt-3 rounded-md border border-accent/30 bg-accent/5 p-3">
            <div className="text-xs text-fog-500">Recommendation</div>
            <div className="text-lg font-semibold">{d.recommendation}</div>
            <p className="mt-1 text-sm text-fog-300"><span className="text-fog-500">Reason: </span>{d.reason}</p>
            <p className="mt-2 text-sm"><span className="text-fog-500">Confidence: </span><span className="num font-semibold">{pct(d.confidence ?? 0)}</span>
              <span className="ml-2 text-xs text-fog-600" title={d.confidence_note}>that this beats the runner-up in simulation</span></p>
          </div>
          <ul className="mt-3 space-y-1.5">
            {d.options?.map((o) => (
              <li key={o.id} className="text-sm">
                <div className="flex items-baseline justify-between gap-2"><span className={o.best ? 'font-medium text-fog-100' : 'text-fog-300'}>{o.label}</span><span className="num">{money(o.value)} <span className="text-xs text-fog-500">±{(o.se * (d.metric === 'expected points' ? 1 : 100)).toFixed(d.metric === 'expected points' ? 2 : 1)}</span></span></div>
                <div className="h-1.5 overflow-hidden rounded bg-ink-800" aria-hidden><div className="h-full" style={{ width: `${Math.min(100, (o.value / (d.metric === 'expected points' ? 3 : 1)) * 100)}%`, background: o.best ? 'rgb(var(--accent))' : '#334357' }} /></div>
              </li>
            ))}
          </ul>
          <div className="mt-3"><Disclaimer>{d.framing} Based on {d.n_rollouts} simulated roll-outs of the {d.horizon}.</Disclaimer></div>
        </div>
      )}
    </div>
  )
}
