import { ChevronDown, ChevronUp, FlaskConical, HelpCircle } from 'lucide-react'
import { useState } from 'react'
import { api } from '../lib/api'
import { cn, errMsg, pct, pp } from '../lib/format'
import { useAsync } from '../lib/hooks'
import type { Analysis, SimResult, Sport } from '../lib/types'
import { Btn, ErrorState, Loading } from './ui'

/** Interface A: the number only. Interface B: the number + "Why?" + a live "Simulate" panel. */
export function PredictionInterface({ variant, sport, state, sessionId, onInteract }: {
  variant: 'A' | 'B'; sport: Sport; state: Record<string, any>; sessionId?: number; onInteract?: (what: string) => void
}) {
  const a = useAsync<Analysis>(() => api.predict(sport, state), [sport, JSON.stringify(state)])
  const meta = useAsync(() => api.meta(sport), [sport], variant === 'B')
  const [why, setWhy] = useState(false)
  const [sim, setSim] = useState<SimResult | null>(null)
  const [simErr, setSimErr] = useState<Error | null>(null)
  const [busy, setBusy] = useState(false)
  const note = (w: string) => onInteract?.(w)

  if (a.error) return <ErrorState error={a.error} onRetry={a.reload} title="Prediction unavailable" />
  if (!a.data) return <Loading label="Loading situation" />
  const d = a.data
  const sb = d.scoreboard
  const runSim = async (id: string) => {
    note(`simulate:${id}`); setBusy(true); setSimErr(null)
    try { setSim(await api.simulate(sport, state, [{ id }], {}, sessionId)) } catch (e) { setSimErr(new Error(`Simulation failed: ${errMsg(e)}`)) } finally { setBusy(false) }
  }
  return (
    <div className="space-y-3">
      <div className="rounded-md border hairline bg-ink-950 p-3">
        <div className="flex items-center justify-between text-xs text-fog-500"><span>{sb.status}</span><span>{sb.clock}</span></div>
        <div className="mt-1 flex justify-between gap-4">{sb.teams.map((t) => <div key={t.name}><div className="text-xs text-fog-300">{t.name}</div><div className="num text-2xl font-semibold">{t.score}</div></div>)}</div>
        {sport === 'cricket' && <p className="mt-1 text-xs text-fog-500">Target {d.state.target} · need {d.state.target - d.state.runs} from {120 - d.state.balls_bowled} balls</p>}
      </div>
      <div className="rounded-md border border-accent/30 bg-accent/5 p-3">
        {d.outcomes.length === 2
          ? <div><div className="text-xs text-fog-500">{d.headline.label} win probability</div><div className="num text-4xl font-semibold">{pct(d.headline.prob)}</div></div>
          : <div><div className="text-xs text-fog-500">Win / draw / loss probability</div><div className="num mt-1 flex flex-wrap gap-x-5 text-lg font-semibold">{d.outcomes.map((o) => <span key={o.cls}>{o.label} <span className="text-accent">{pct(o.prob)}</span></span>)}</div></div>}
      </div>
      {variant === 'B' && d.explanation && (
        <>
          <div>
            <Btn variant="ghost" onClick={() => { setWhy(!why); note('why-toggle') }} aria-expanded={why}><HelpCircle className="h-4 w-4" aria-hidden /> Why? {why ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}</Btn>
            {why && (
              <div className="mt-2 grid gap-2 rounded-md border hairline p-3 sm:grid-cols-2" role="region" aria-label="Explanation">
                <div><h4 className="mb-1 text-xs font-medium text-up">Helping</h4><ul className="space-y-1 text-sm">{d.explanation.simple.positives.map((p, i) => <li key={i}><span className="num mr-1 text-up">+{p.pp.toFixed(1)}</span>{p.text}</li>)}{!d.explanation.simple.positives.length && <li className="text-fog-500">None strong</li>}</ul></div>
                <div><h4 className="mb-1 text-xs font-medium text-down">Hurting</h4><ul className="space-y-1 text-sm">{d.explanation.simple.negatives.map((p, i) => <li key={i}><span className="num mr-1 text-down">{p.pp.toFixed(1)}</span>{p.text}</li>)}{!d.explanation.simple.negatives.length && <li className="text-fog-500">None strong</li>}</ul></div>
              </div>
            )}
          </div>
          <div className="rounded-md border hairline p-3">
            <div className="mb-2 flex items-center gap-1.5 text-sm font-medium"><FlaskConical className="h-4 w-4 text-accent" aria-hidden /> Simulate</div>
            {!meta.data ? <Loading height="h-10" /> : <div className="flex flex-wrap gap-1.5">{meta.data.events.map((e) => <button key={e.id} disabled={busy} onClick={() => runSim(e.id)} className="rounded-md border hairline bg-ink-950 px-2 py-1 text-xs hover:border-accent hover:text-accent disabled:opacity-50">{e.label}</button>)}</div>}
            {simErr && <div className="mt-2"><ErrorState error={simErr} /></div>}
            {sim && !simErr && (
              <p className="mt-2 text-sm" aria-live="polite">After <b>{sim.applied[0].label}</b>: <span className="num">{pct(sim.deltas[sim.focus_class].before)} → <b>{pct(sim.deltas[sim.focus_class].after)}</b></span> <span className={cn('num', sim.deltas[sim.focus_class].delta_pp >= 0 ? 'text-up' : 'text-down')}>({pp(sim.deltas[sim.focus_class].delta_pp)})</span> for {sim.deltas[sim.focus_class].label}</p>
            )}
          </div>
        </>
      )}
    </div>
  )
}
