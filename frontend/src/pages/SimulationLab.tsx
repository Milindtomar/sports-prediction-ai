import { ArrowRight, FlaskConical, Minus, Plus, RotateCcw, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Bar, BarChart, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { TimelineControls } from '../components/match/Controls'
import { ScoreHeader } from '../components/match/Cards'
import { AnimatedNumber, Btn, Disclaimer, ErrorState, Loading, Panel, Pill } from '../components/ui'
import { api } from '../lib/api'
import { cn, errMsg, pct, pp, signed } from '../lib/format'
import { useAsync, useDebounced } from '../lib/hooks'
import { useMatch } from '../lib/MatchContext'
import type { SimResult, Sport } from '../lib/types'

const EDITABLE: Record<Sport, { key: string; label: string; min: number; max: number; step?: number }[]> = {
  cricket: [{ key: 'runs', label: 'Runs', min: 0, max: 300 }, { key: 'wickets', label: 'Wickets lost', min: 0, max: 9 }, { key: 'balls_bowled', label: 'Balls bowled', min: 0, max: 119 }],
  football: [{ key: 'minute', label: 'Minute', min: 0, max: 89 }, { key: 'home_red', label: 'Home reds', min: 0, max: 2 }, { key: 'away_red', label: 'Away reds', min: 0, max: 2 }],
  basketball: [{ key: 'elapsed_sec', label: 'Seconds elapsed', min: 0, max: 2879, step: 30 }, { key: 'home_score', label: 'Home score', min: 0, max: 160 }, { key: 'away_score', label: 'Away score', min: 0, max: 160 }],
}

export default function SimulationLab() {
  const { sport, meta, state, analysis, step } = useMatch()
  const [queue, setQueue] = useState<{ id: string; count: number }[]>([])
  const [overrides, setOverrides] = useState<Record<string, number>>({})
  const [result, setResult] = useState<SimResult | null>(null)
  const [running, setRunning] = useState(false)
  const [err, setErr] = useState<Error | null>(null)
  const eventsByGroup = useMemo(() => {
    const g: Record<string, NonNullable<typeof meta.data>['events']> = {}
    meta.data?.events.forEach((e) => { (g[e.group] ??= []).push(e) })
    return g
  }, [meta.data])
  const merged = useMemo(() => (state ? { ...state, ...overrides } : null), [state, overrides])
  const dMerged = useDebounced(merged, 350)
  const sweep = useAsync(() => api.sweep(sport, dMerged!), [sport, JSON.stringify(dMerged)], !!dMerged)
  const base = analysis.data

  // changing the match moment or sport resets the scenario
  const resetKey = `${sport}-${step}`
  const [lastKey, setLastKey] = useState(resetKey)
  if (lastKey !== resetKey) { setLastKey(resetKey); setQueue([]); setOverrides({}); setResult(null); setErr(null) }

  const add = (id: string) => setQueue((q) => { const i = q.findIndex((x) => x.id === id); return i >= 0 ? q.map((x, j) => (j === i ? { ...x, count: Math.min(6, x.count + 1) } : x)) : [...q, { id, count: 1 }] })
  const dec = (id: string) => setQueue((q) => q.flatMap((x) => (x.id === id ? (x.count > 1 ? [{ ...x, count: x.count - 1 }] : []) : [x])))
  const label = (id: string) => meta.data?.events.find((e) => e.id === id)?.label ?? id

  const run = async () => {
    if (!state || !queue.length) return
    setRunning(true); setErr(null)
    try { setResult(await api.simulate(sport, state, queue, overrides)) }
    catch (e) { setErr(new Error(`Simulation failed: ${errMsg(e)}`)); setResult(null) }
    finally { setRunning(false) }
  }

  const d = result?.deltas[result.focus_class]
  return (
    <div className="space-y-3">
      <TimelineControls />
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="space-y-3">
          {base ? <ScoreHeader a={base} /> : <Loading height="h-32" />}
          <Panel title="1 · Current state" subtitle="Optionally edit the situation before simulating">
            <div className="grid grid-cols-3 gap-2">
              {EDITABLE[sport].map((f) => (
                <label key={f.key} className="text-xs text-fog-500">{f.label}
                  <input type="number" min={f.min} max={f.max} step={f.step ?? 1} value={overrides[f.key] ?? state?.[f.key] ?? 0}
                    onChange={(e) => setOverrides((o) => ({ ...o, [f.key]: +e.target.value }))} aria-label={f.label}
                    className="num mt-1 w-full rounded-md border hairline bg-ink-950 px-2 py-1.5 text-sm text-fog-100" />
                </label>
              ))}
            </div>
            {Object.keys(overrides).length > 0 && <Btn variant="quiet" className="mt-2" onClick={() => setOverrides({})}><RotateCcw className="h-3.5 w-3.5" /> Reset edits</Btn>}
            {base && <p className="mt-3 text-sm"><span className="text-fog-500">Current: </span><span className="num font-semibold">{base.headline.label} {pct(base.headline.prob)}</span></p>}
          </Panel>
          <Panel title="2 · Choose events" subtitle="Click to add; click again to repeat (max 6)">
            {meta.error ? <ErrorState error={meta.error} onRetry={meta.reload} /> : !meta.data ? <Loading /> : (
              <div className="space-y-3">
                {Object.entries(eventsByGroup).map(([g, evs]) => (
                  <div key={g}><div className="mb-1 text-xs text-fog-500">{g}</div>
                    <div className="flex flex-wrap gap-1.5">{evs.map((e) => (
                      <button key={e.id} onClick={() => add(e.id)} title={e.description} className="flex items-center gap-1 rounded-md border hairline bg-ink-950 px-2 py-1 text-xs text-fog-100 hover:border-accent hover:text-accent"><Plus className="h-3 w-3" aria-hidden />{e.label}</button>))}</div></div>
                ))}
              </div>
            )}
          </Panel>
          <Panel title="3 · Run" subtitle="Events are applied in order, then re-predicted by the trained model">
            {queue.length === 0 ? <p className="text-sm text-fog-500">No events selected yet. Pick at least one above.</p> : (
              <ol className="mb-3 space-y-1">{queue.map((q, i) => (
                <li key={q.id} className="flex items-center justify-between rounded border hairline px-2 py-1 text-sm"><span><span className="num mr-2 text-fog-600">{i + 1}</span>{label(q.id)}{q.count > 1 && <span className="num ml-1 text-accent">×{q.count}</span>}</span>
                  <span className="flex"><button aria-label={`Remove one ${label(q.id)}`} onClick={() => dec(q.id)} className="rounded p-1 text-fog-500 hover:text-down"><Minus className="h-3.5 w-3.5" /></button></span></li>))}</ol>
            )}
            <div className="flex gap-2"><Btn onClick={run} disabled={!queue.length || running || !state} className="flex-1"><FlaskConical className="h-4 w-4" aria-hidden /> {running ? 'Simulating…' : 'Simulate'}</Btn>
              <Btn variant="ghost" onClick={() => { setQueue([]); setResult(null); setErr(null) }} disabled={!queue.length && !result} aria-label="Clear scenario"><X className="h-4 w-4" /></Btn></div>
          </Panel>
        </div>

        <div className="space-y-3">
          {err && <ErrorState error={err} onRetry={run} title="Simulation failed" />}
          <Panel title="Before → after" subtitle="Probabilities from the real prediction pipeline, not edited numbers" actions={result && <Pill tone="model">MODEL PREDICTION</Pill>}>
            {!result ? <p className="py-10 text-center text-sm text-fog-500">Run a simulation to see the new probability, what changed, and why.</p> : (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                  <div><div className="text-xs text-fog-500">{d!.label} · before</div><div className="num text-4xl font-semibold text-fog-300">{pct(d!.before)}</div></div>
                  <ArrowRight className="h-6 w-6 text-fog-600" aria-hidden />
                  <div><div className="text-xs text-fog-500">after {result.applied.map((a) => a.label + (a.count > 1 ? ` ×${a.count}` : '')).join(' → ')}</div>
                    <AnimatedNumber value={d!.after * 100} format={(v) => `${v.toFixed(0)}%`} className="num text-5xl font-semibold" /></div>
                  <div className={cn('num rounded-md border px-2.5 py-1 text-lg font-semibold', d!.delta_pp >= 0 ? 'border-up/40 text-up' : 'border-down/40 text-down')}>{pp(d!.delta_pp)}</div>
                </div>
                {result.deltas.length === 3 && <div className="grid grid-cols-3 gap-2 text-xs">{result.deltas.map((x) => <div key={x.label} className="rounded border hairline p-2"><div className="truncate text-fog-500">{x.label}</div><div className="num">{pct(x.before)} → <b>{pct(x.after)}</b> <span className={x.delta_pp >= 0 ? 'text-up' : 'text-down'}>{signed(x.delta_pp)}</span></div></div>)}</div>}
                <p className="text-sm leading-relaxed text-fog-300"><span className="font-medium text-fog-100">Why it moved: </span>{result.narrative}</p>
                {result.after.terminal && <Pill tone="warn">The match is decided in the resulting state</Pill>}
                {result.attribution && (
                  <div>
                    <h4 className="mb-1 text-xs font-medium text-fog-300">Impact by changed factor (percentage points)</h4>
                    <ResponsiveContainer width="100%" height={Math.max(110, result.attribution.rows.length * 28 + 20)}>
                      <BarChart data={result.attribution.rows} layout="vertical" margin={{ left: 4, right: 28, top: 4, bottom: 0 }}>
                        <XAxis type="number" stroke="#334357" /><YAxis type="category" dataKey="label" width={170} stroke="#334357" tick={{ fontSize: 11 }} />
                        <ReferenceLine x={0} stroke="#66737F" />
                        <Tooltip cursor={{ fill: '#18222B' }} contentStyle={{ background: '#121A21', border: '1px solid #243040', borderRadius: 8, fontSize: 12 }} formatter={(v: any, _n, p: any) => [`${signed(v, 2)} pp (${p.payload.before_text} → ${p.payload.after_text})`, 'Contribution']} />
                        <Bar dataKey="contribution_pp" isAnimationActive={false} radius={2}>{result.attribution.rows.map((r) => <Cell key={r.feature} fill={r.contribution_pp >= 0 ? '#5FD39A' : '#F0646E'} />)}</Bar>
                      </BarChart>
                    </ResponsiveContainer>
                    <p className="text-[11px] text-fog-600">{result.attribution.method}</p>
                  </div>
                )}
                <details className="text-xs text-fog-500"><summary className="cursor-pointer text-fog-300">How was this computed?</summary>
                  <ol className="mt-1 list-decimal pl-5">{result.pipeline.map((p) => <li key={p}>{p}</li>)}</ol></details>
              </div>
            )}
          </Panel>
          <Panel title="Impact of every single event" subtitle="Effect on the headline probability if the event happened next (one batched model call)" actions={sweep.loading && <span className="text-xs text-fog-500">updating…</span>}>
            {sweep.error ? <ErrorState error={sweep.error} onRetry={sweep.reload} /> : !sweep.data ? <Loading /> : (
              <>
                <ResponsiveContainer width="100%" height={sweep.data.impacts.length * 30 + 20}>
                  <BarChart data={sweep.data.impacts} layout="vertical" margin={{ left: 4, right: 36, top: 2, bottom: 0 }} onClick={(e: any) => { const id = e?.activePayload?.[0]?.payload?.id; if (id) add(id) }}>
                    <XAxis type="number" stroke="#334357" tickFormatter={(v) => `${v}`} /><YAxis type="category" dataKey="label" width={190} stroke="#334357" tick={{ fontSize: 11 }} />
                    <ReferenceLine x={0} stroke="#66737F" />
                    <Tooltip cursor={{ fill: '#18222B' }} contentStyle={{ background: '#121A21', border: '1px solid #243040', borderRadius: 8, fontSize: 12 }} formatter={(v: any) => [`${signed(v, 1)} pp`, `${sweep.data!.focus_label} win probability`]} />
                    <Bar dataKey="delta_pp" isAnimationActive={false} radius={2} cursor="pointer">{sweep.data.impacts.map((r) => <Cell key={r.id} fill={r.delta_pp >= 0 ? '#5FD39A' : '#F0646E'} />)}</Bar>
                  </BarChart>
                </ResponsiveContainer>
                <p className="text-[11px] text-fog-600">Baseline {pct(sweep.data.baseline, 1)} for {sweep.data.focus_label}. Click a bar to add that event to your scenario.</p>
              </>
            )}
          </Panel>
          <Disclaimer>What-if outcomes describe how the trained model responds to a hypothetical state. They are estimates under the simulator's assumptions, not predictions of what will happen.</Disclaimer>
        </div>
      </div>
    </div>
  )
}
