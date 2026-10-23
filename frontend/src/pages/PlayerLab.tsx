import { useEffect, useMemo, useState } from 'react'
import { CartesianGrid, Legend, Line, LineChart, PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Disclaimer, EmptyState, ErrorState, Loading, Panel, Pill, Segmented } from '../components/ui'
import { api } from '../lib/api'
import { cn } from '../lib/format'
import { useAsync } from '../lib/hooks'
import { useMatch } from '../lib/MatchContext'
import type { PlayerNext, PlayerRow } from '../lib/types'

const KIND_LABEL: Record<string, string> = { bat: 'Batting', bowl: 'Bowling', main: 'Match performance' }
const TARGET_LABEL: Record<string, string> = { runs: 'Predicted runs', p50: 'Probability of 50+', wickets: 'Expected wickets', economy: 'Expected economy', goals: 'Expected goals', assists: 'Expected assists', shots: 'Expected shots', points: 'Expected points', rebounds: 'Expected rebounds' }

function PredictionCards({ next, kind }: { next: PlayerNext; kind: string }) {
  const k = next.kinds[kind]
  if (!k) return null
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {Object.entries(k.predictions).map(([t, v]) => (
        <div key={t} className="rounded-md border hairline p-3">
          <div className="text-xs text-fog-500">{TARGET_LABEL[t] ?? t}</div>
          <div className="num text-2xl font-semibold">{t === 'p50' ? `${(v.value * 100).toFixed(0)}%` : v.value.toFixed(1)}</div>
          <div className="num text-[11px] text-fog-600">{v.lo != null ? `likely ${v.lo.toFixed(1)}–${v.hi!.toFixed(1)}` : 'calibrated probability'}</div>
        </div>
      ))}
      <div className="rounded-md border border-accent/40 bg-accent/5 p-3">
        <div className="text-xs text-fog-500">Performance score</div>
        <div className="num text-2xl font-semibold text-accent">{k.performance_score.toFixed(0)}<span className="text-sm text-fog-500">/100</span></div>
        <div className="text-[11px] text-fog-600">composite of predicted stats</div>
      </div>
    </div>
  )
}

export default function PlayerLab() {
  const { sport } = useMatch()
  const players = useAsync(() => api.players(sport), [sport])
  const [team, setTeam] = useState<string>('')
  const [aId, setAId] = useState<number | null>(null)
  const [bId, setBId] = useState<number | null>(null)
  const [kind, setKind] = useState<string>('')
  const [ctx, setCtx] = useState<{ opp: number; par: number; home: number }>({ opp: 0, par: 158, home: 1 })
  const teams = useMemo(() => [...new Set(players.data?.map((p) => p.team))], [players.data])
  useEffect(() => { setAId(null); setBId(null); setKind(''); setTeam('') }, [sport])
  useEffect(() => { if (players.data?.length && !team) setTeam(players.data[0].team) }, [players.data, team])
  const list = players.data?.filter((p) => p.team === team) ?? []
  useEffect(() => { if (list.length && (aId == null || !players.data?.some((p) => p.id === aId))) setAId(list[0].id) }, [team, players.data])

  const detail = useAsync(() => api.player(aId!), [aId], aId != null)
  const d = detail.data
  const kinds = d ? Object.keys(d.next_game.kinds) : []
  const activeKind = kind && kinds.includes(kind) ? kind : kinds[0]
  const nextCtx = useAsync(() => api.playerPredict(aId!, sport === 'cricket' ? { opp_strength: ctx.opp, venue_par: ctx.par } : { opp_strength: ctx.opp, home: ctx.home }), [aId, ctx.opp, ctx.par, ctx.home, sport], aId != null)
  const next = nextCtx.data ?? d?.next_game
  const [target, setTarget] = useState('')
  const hist = d && activeKind ? d.history.kinds[activeKind] : undefined
  const targets = hist?.length ? Object.keys(hist[0].predicted).filter((t) => hist[0].actual[t] != null) : []
  const tgt = targets.includes(target) ? target : targets[0]
  const cmp = useAsync(() => api.compare(aId!, bId!), [aId, bId], aId != null && bId != null && aId !== bId)
  const radar = useMemo(() => {
    if (!cmp.data) return []
    return cmp.data.a.percentiles.map((p: any, i: number) => ({ metric: p.label, a: p.percentile, b: cmp.data.b.percentiles[i]?.percentile ?? 0 }))
  }, [cmp.data])

  if (players.error) return <ErrorState error={players.error} onRetry={players.reload} title="Players could not load" />
  if (players.data && !players.data.length) return <EmptyState title="No players found" hint="Seed the database with `python -m app.seed`." />

  return (
    <div className="grid grid-cols-1 gap-3 xl:grid-cols-[280px_minmax(0,1fr)]">
      <div className="space-y-3">
        <Panel title="Squad" pad={false}>
          <div className="border-b hairline p-3"><select aria-label="Team" value={team} onChange={(e) => { setTeam(e.target.value); setAId(null) }} className="w-full rounded-md border hairline bg-ink-950 px-2 py-1.5 text-sm">{teams.map((t) => <option key={t}>{t}</option>)}</select></div>
          {!players.data ? <Loading /> : (
            <ul className="max-h-[520px] divide-y divide-ink-700 overflow-auto scroll-thin">
              {list.map((p: PlayerRow) => (
                <li key={p.id}><button onClick={() => setAId(p.id)} aria-current={p.id === aId} className={cn('flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-ink-800', p.id === aId && 'bg-ink-800')}>
                  <span className="truncate">{p.name}</span><Pill>{p.role}</Pill></button></li>
              ))}
            </ul>
          )}
        </Panel>
        <Panel title="Compare with" subtitle="Pick a second player of the same sport">
          <select aria-label="Compare with" value={bId ?? ''} onChange={(e) => setBId(e.target.value ? +e.target.value : null)} className="w-full rounded-md border hairline bg-ink-950 px-2 py-1.5 text-sm">
            <option value="">No comparison</option>
            {players.data?.filter((p) => p.id !== aId).map((p) => <option key={p.id} value={p.id}>{p.name} · {p.team}</option>)}
          </select>
        </Panel>
      </div>

      <div className="min-w-0 space-y-3">
        {detail.error && <ErrorState error={detail.error} onRetry={detail.reload} title="Player data unavailable" />}
        {!d && !detail.error && <Loading label="Loading player" height="h-60" />}
        {d && next && (
          <>
            <Panel title={d.player.name} subtitle={`${d.player.team} · ${d.player.role}`} actions={kinds.length > 1 && <Segmented label="Discipline" value={activeKind} onChange={setKind} options={kinds.map((k) => ({ value: k, label: KIND_LABEL[k] }))} />}>
              <div className="mb-3 flex flex-wrap items-center gap-3">
                <Pill tone="model">MODEL PREDICTION · next game</Pill>
                <label className="flex items-center gap-2 text-xs text-fog-500">Opposition strength
                  <input type="range" min={-2} max={2} step={0.25} value={ctx.opp} onChange={(e) => setCtx({ ...ctx, opp: +e.target.value })} aria-label="Opposition strength" className="accent-[rgb(var(--accent))]" /><span className="num w-10 text-fog-100">{ctx.opp > 0 ? '+' : ''}{ctx.opp.toFixed(2)}</span></label>
                {sport === 'cricket' ? (
                  <label className="flex items-center gap-2 text-xs text-fog-500">Venue par<input type="range" min={130} max={185} value={ctx.par} onChange={(e) => setCtx({ ...ctx, par: +e.target.value })} aria-label="Venue par score" className="accent-[rgb(var(--accent))]" /><span className="num w-8 text-fog-100">{ctx.par}</span></label>
                ) : (
                  <Segmented label="Venue" value={String(ctx.home)} onChange={(v) => setCtx({ ...ctx, home: +v })} options={[{ value: '1', label: 'Home' }, { value: '0', label: 'Away' }]} />
                )}
                {nextCtx.loading && <span className="text-xs text-fog-500">updating…</span>}
              </div>
              {nextCtx.error ? <ErrorState error={nextCtx.error} onRetry={nextCtx.reload} /> : <PredictionCards next={next} kind={activeKind} />}
              <p className="mt-2 text-[11px] text-fog-600">Ranges are the 10th–90th percentile of past test errors. Based on {next.kinds[activeKind]?.n_games} previous games.</p>
            </Panel>

            <Panel title="Historical performance" subtitle="MODEL PREDICTION (made only from earlier games) versus ACTUAL RESULT" actions={targets.length > 1 && <Segmented label="Statistic" value={tgt} onChange={setTarget} options={targets.map((t) => ({ value: t, label: t }))} />}>
              {!hist?.length ? <EmptyState title="No history yet" hint="This player has fewer than four recorded games." /> : (
                <div role="img" aria-label="Predicted versus actual per game">
                  <ResponsiveContainer width="100%" height={240}>
                    <LineChart data={hist.map((h) => ({ game: h.game + 1, predicted: +h.predicted[tgt].toFixed(2), actual: h.actual[tgt] }))} margin={{ top: 8, right: 8, left: -14, bottom: 0 }}>
                      <CartesianGrid stroke="#243040" strokeDasharray="2 4" vertical={false} /><XAxis dataKey="game" stroke="#334357" /><YAxis stroke="#334357" />
                      <Tooltip contentStyle={{ background: '#121A21', border: '1px solid #243040', borderRadius: 8, fontSize: 12 }} />
                      <Legend wrapperStyle={{ fontSize: 12 }} />
                      <Line dataKey="actual" name="ACTUAL RESULT" stroke="#B4BEC9" strokeWidth={1.6} dot={{ r: 2.5 }} isAnimationActive={false} />
                      <Line dataKey="predicted" name="MODEL PREDICTION" stroke="rgb(var(--accent))" strokeWidth={2.4} strokeDasharray="5 3" dot={false} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Panel>

            <Panel title="Strengths and weaknesses" subtitle="Compared with role peers in this database">
              {d.profile.kinds[activeKind] && (() => {
                const pk = d.profile.kinds[activeKind]
                return (
                  <div className="space-y-3">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div><h4 className="mb-1 text-xs font-medium text-up">Strengths</h4>{pk.strengths.length ? <ul className="space-y-1 text-sm">{pk.strengths.map((s: any) => <li key={s.feature}>{s.label} <span className="num text-fog-500">· {s.percentile}th percentile</span></li>)}</ul> : <p className="text-sm text-fog-500">No standout strengths versus peers.</p>}</div>
                      <div><h4 className="mb-1 text-xs font-medium text-down">Weaknesses</h4>{pk.weaknesses.length ? <ul className="space-y-1 text-sm">{pk.weaknesses.map((s: any) => <li key={s.feature}>{s.label} <span className="num text-fog-500">· {s.percentile}th percentile</span></li>)}</ul> : <p className="text-sm text-fog-500">No clear weaknesses versus peers.</p>}</div>
                    </div>
                    {pk.notes.map((n: string) => <p key={n} className="text-sm text-warn">{n}</p>)}
                    <table className="w-full text-xs"><thead className="text-left text-fog-500"><tr><th className="py-1 font-medium">Metric</th><th className="font-medium">Player</th><th className="font-medium">Peer mean</th><th className="text-right font-medium">Percentile</th></tr></thead>
                      <tbody className="divide-y divide-ink-700">{pk.metrics.map((m) => <tr key={m.feature}><td className="py-1.5">{m.label}</td><td className="num">{m.value.toFixed(2)}</td><td className="num text-fog-500">{m.peer_mean.toFixed(2)}</td><td className="num text-right">{m.percentile}</td></tr>)}</tbody></table>
                    <p className="text-[11px] text-fog-600">{pk.method}</p>
                  </div>
                )
              })()}
            </Panel>
          </>
        )}

        {bId != null && (
          <Panel title="Player comparison" subtitle="Percentile among role peers (higher is better)">
            {cmp.error ? <ErrorState error={cmp.error} onRetry={cmp.reload} /> : !cmp.data ? <Loading /> : (
              <div className="grid gap-4 lg:grid-cols-2">
                <div role="img" aria-label="Radar comparison"><ResponsiveContainer width="100%" height={280}>
                  <RadarChart data={radar}><PolarGrid stroke="#243040" /><PolarAngleAxis dataKey="metric" tick={{ fill: '#B4BEC9', fontSize: 11 }} />
                    <Radar name={cmp.data.a.player.name} dataKey="a" stroke="rgb(var(--accent))" fill="rgb(var(--accent))" fillOpacity={0.25} isAnimationActive={false} />
                    <Radar name={cmp.data.b.player.name} dataKey="b" stroke="#B4BEC9" fill="#B4BEC9" fillOpacity={0.15} isAnimationActive={false} /><Legend wrapperStyle={{ fontSize: 12 }} /><Tooltip contentStyle={{ background: '#121A21', border: '1px solid #243040', borderRadius: 8, fontSize: 12 }} /></RadarChart></ResponsiveContainer></div>
                <table className="h-fit w-full text-sm"><thead className="text-left text-xs text-fog-500"><tr><th className="py-1 font-medium">Next game (MODEL PREDICTION)</th><th className="font-medium">{cmp.data.a.player.name}</th><th className="font-medium">{cmp.data.b.player.name}</th></tr></thead>
                  <tbody className="divide-y divide-ink-700">{Object.keys(cmp.data.a.next?.predictions ?? {}).map((t) => (
                    <tr key={t}><td className="py-1.5 text-fog-300">{TARGET_LABEL[t] ?? t}</td><td className="num">{t === 'p50' ? `${(cmp.data.a.next.predictions[t].value * 100).toFixed(0)}%` : cmp.data.a.next.predictions[t].value.toFixed(1)}</td><td className="num">{cmp.data.b.next?.predictions[t] ? (t === 'p50' ? `${(cmp.data.b.next.predictions[t].value * 100).toFixed(0)}%` : cmp.data.b.next.predictions[t].value.toFixed(1)) : '–'}</td></tr>))}
                    <tr><td className="py-1.5 text-fog-300">Performance score</td><td className="num text-accent">{cmp.data.a.next?.performance_score}</td><td className="num">{cmp.data.b.next?.performance_score ?? '–'}</td></tr></tbody></table>
              </div>
            )}
          </Panel>
        )}
        {next && <Disclaimer>{next.disclaimer}</Disclaimer>}
      </div>
    </div>
  )
}
