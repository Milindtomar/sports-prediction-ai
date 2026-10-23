import * as d3 from 'd3'
import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

type Ev = Record<string, any>
type St = Record<string, any>
const tip = { background: '#121A21', border: '1px solid #243040', borderRadius: 8, fontSize: 12 }

export const seenBalls = (events: Ev[], st: St) =>
  events.filter((e) => e.inn < st.innings || (e.inn === st.innings && e.over * 6 + e.ball < st.balls_bowled))

export function RunRateChart({ timeline, step }: { timeline: St[]; step: number }) {
  const cur = timeline[step]
  const pts = timeline.slice(0, step + 1).filter((s) => s.innings === cur.innings && s.balls_bowled > 0)
  const data = pts.map((s, i) => {
    const prev = i ? pts[i - 1] : { runs: 0, balls_bowled: 0 }
    const ov = s.balls_bowled / 6
    return {
      over: +ov.toFixed(1), crr: +(s.runs / ov).toFixed(2),
      rrr: s.innings === 2 && s.balls_bowled < 120 ? +Math.min(((s.target - s.runs) * 6) / (120 - s.balls_bowled), 30).toFixed(2) : null,
      perOver: s.runs - prev.runs,
    }
  })
  if (!data.length) return <p className="py-8 text-center text-sm text-fog-500">Run-rate data appears once the first over is bowled.</p>
  return (
    <div role="img" aria-label="Run rate by over">
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          <CartesianGrid stroke="#243040" strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="over" stroke="#334357" />
          <YAxis yAxisId="r" stroke="#334357" /><YAxis yAxisId="o" orientation="right" stroke="#334357" hide />
          <Bar yAxisId="o" dataKey="perOver" name="Runs in over" fill="#334357" radius={[2, 2, 0, 0]} isAnimationActive={false} />
          <Line yAxisId="r" dataKey="crr" name="Current RR" stroke="rgb(var(--accent))" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line yAxisId="r" dataKey="rrr" name="Required RR" stroke="#F0646E" strokeDasharray="4 3" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
          <Tooltip contentStyle={tip} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

export function ScoreProgression({ timeline, step }: { timeline: St[]; step: number }) {
  const cur = timeline[step]
  const byOver: Record<number, any> = {}
  timeline.forEach((s, i) => {
    const o = Math.round(s.balls_bowled / 6)
    byOver[o] = byOver[o] ?? { over: o }
    if (s.innings === 1) byOver[o].inn1 = s.runs
    else if (i <= step) byOver[o].inn2 = s.runs
  })
  const data = Object.values(byOver).sort((a, b) => a.over - b.over)
  const target = timeline.find((s) => s.target)?.target
  return (
    <div role="img" aria-label="Score progression by over for both innings">
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid stroke="#243040" strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="over" stroke="#334357" /><YAxis stroke="#334357" domain={[0, 'dataMax + 10']} />
          <Line dataKey="inn1" name="1st innings" stroke="#B4BEC9" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
          <Line dataKey="inn2" name="2nd innings" stroke="rgb(var(--accent))" strokeWidth={2.4} dot={false} isAnimationActive={false} connectNulls />
          {cur.venue_par && <Line dataKey={() => undefined} />}
          <Tooltip contentStyle={tip} />
        </ComposedChart>
      </ResponsiveContainer>
      {target && <p className="text-center text-xs text-fog-500">Target {target}</p>}
    </div>
  )
}

export function PartnershipPanel({ events, st }: { events: Ev[]; st: St }) {
  const balls = seenBalls(events, st).filter((e) => e.inn === st.innings)
  const parts: { name: string; runs: number; balls: number; pair: string }[] = []
  let runs = 0, n = 0, pair = new Set<string>()
  balls.forEach((e) => {
    runs += e.runs; n += 1; pair.add(e.striker)
    if (e.wicket) { parts.push({ name: `W${parts.length + 1}`, runs, balls: n, pair: [...pair].join(' & ') }); runs = 0; n = 0; pair = new Set() }
  })
  if (n) parts.push({ name: 'Now', runs, balls: n, pair: [...pair].join(' & ') })
  if (!parts.length) return <p className="py-8 text-center text-sm text-fog-500">No partnerships yet.</p>
  const max = Math.max(...parts.map((p) => p.runs), 1)
  return (
    <ul className="space-y-2">
      {parts.map((p, i) => (
        <li key={i} title={p.pair}>
          <div className="flex justify-between text-xs"><span className="truncate text-fog-300">{p.name} · {p.pair || '–'}</span><span className="num text-fog-100">{p.runs} ({p.balls})</span></div>
          <div className="mt-0.5 h-1.5 rounded bg-ink-800" aria-hidden><div className="h-full rounded" style={{ width: `${(p.runs / max) * 100}%`, background: p.name === 'Now' ? 'rgb(var(--accent))' : '#66737F' }} /></div>
        </li>
      ))}
    </ul>
  )
}

/** Wagon wheel: polar plot of shot direction/distance. Angle 0° = straight down the ground. Illustrative placement. */
export function WagonWheel({ events, st }: { events: Ev[]; st: St }) {
  const R = 130, c = 150
  const shots = seenBalls(events, st).filter((e) => e.inn === st.innings && e.runs > 0 && e.angle != null)
  const r = d3.scaleLinear().domain([0, 1.25]).range([0, R])
  const sectors = d3.range(8)
  const arc = d3.arc<number>().innerRadius(0).outerRadius(r(1.0)).startAngle((i) => (i * Math.PI) / 4).endAngle((i) => ((i + 1) * Math.PI) / 4)
  const col = (runs: number) => (runs === 6 ? '#F0B35A' : runs === 4 ? 'rgb(var(--accent))' : '#8794A3')
  return (
    <figure>
      <svg viewBox="0 0 300 300" className="mx-auto w-full max-w-[340px]" role="img" aria-label={`Wagon wheel with ${shots.length} scoring shots`}>
        <g transform={`translate(${c},${c})`}>
          {sectors.map((i) => <path key={i} d={arc(i) ?? ''} fill={i % 2 ? '#121A21' : '#0E1419'} stroke="#243040" />)}
          <circle r={r(0.5)} fill="none" stroke="#243040" strokeDasharray="3 3" />
          <circle r={r(1.0)} fill="none" stroke="#334357" />
          <rect x={-4} y={-14} width={8} height={28} fill="#243040" rx={1} />
          {shots.map((e, i) => {
            const th = (e.angle * Math.PI) / 180, rr = r(e.dist)
            return <line key={i} x1={0} y1={0} x2={rr * Math.sin(th)} y2={-rr * Math.cos(th)} stroke={col(e.runs)} strokeWidth={e.runs >= 4 ? 1.8 : 1} opacity={0.85}><title>{`${e.striker}: ${e.runs}`}</title></line>
          })}
        </g>
      </svg>
      <figcaption className="mt-1 flex justify-center gap-4 text-[11px] text-fog-500"><span><i className="mr-1 inline-block h-0.5 w-3 bg-fog-500 align-middle" />1–3</span><span><i className="mr-1 inline-block h-0.5 w-3 bg-accent align-middle" />four</span><span><i className="mr-1 inline-block h-0.5 w-3 bg-warn align-middle" />six</span></figcaption>
    </figure>
  )
}

/** Bowling / pitch map: where deliveries landed (length) and line. Illustrative placement. */
export function PitchMap({ events, st }: { events: Ev[]; st: St }) {
  const balls = seenBalls(events, st).filter((e) => e.inn === st.innings).slice(-36)
  const W = 150, H = 280
  const col = (e: Ev) => (e.wicket ? '#F0646E' : e.runs >= 4 ? 'rgb(var(--accent))' : e.runs === 0 ? '#66737F' : '#B4BEC9')
  const zones = [['Short', 0.75, 1], ['Good', 0.4, 0.75], ['Full', 0.15, 0.4], ['Yorker', 0, 0.15]] as const
  const y = (len: number) => H - 14 - len * (H - 28)
  return (
    <figure>
      <svg viewBox={`0 0 ${W} ${H}`} className="mx-auto h-[280px] w-auto" role="img" aria-label={`Pitch map of the last ${balls.length} deliveries`}>
        <rect x={25} y={4} width={W - 50} height={H - 8} rx={4} fill="#121A21" stroke="#243040" />
        {zones.map(([n, a, b]) => <g key={n}><line x1={25} x2={W - 25} y1={y(b)} y2={y(b)} stroke="#243040" strokeDasharray="3 3" /><text x={W - 22} y={y((a + b) / 2) + 3} fontSize={8} fill="#66737F">{n}</text></g>)}
        {[-0.2, 0, 0.2].map((x) => <rect key={x} x={W / 2 + x * 60 - 1.5} y={H - 12} width={3} height={8} fill="#8794A3" />)}
        {balls.map((e, i) => <circle key={i} cx={W / 2 + e.line * 45} cy={y(e.length)} r={4} fill={col(e)} opacity={0.9}><title>{`${e.bowler} → ${e.runs}${e.wicket ? ' W' : ''}`}</title></circle>)}
      </svg>
      <figcaption className="mt-1 text-center text-[11px] text-fog-500">Last {balls.length} deliveries · red = wicket, green = boundary</figcaption>
    </figure>
  )
}
