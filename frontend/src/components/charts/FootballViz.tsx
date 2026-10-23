import { CartesianGrid, Line, LineChart, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

type Ev = Record<string, any>
type St = Record<string, any>
const tip = { background: '#121A21', border: '1px solid #243040', borderRadius: 8, fontSize: 12 }

export function ShotMap({ events, st, home, away }: { events: Ev[]; st: St; home: string; away: string }) {
  const shots = events.filter((e) => e.type === 'shot' && e.minute <= st.minute)
  return (
    <figure>
      <svg viewBox="0 0 105 68" className="w-full rounded border hairline bg-[#0C1A14]" role="img" aria-label={`Shot map with ${shots.length} shots`}>
        <g fill="none" stroke="#27483A" strokeWidth={0.35}>
          <rect x={0.5} y={0.5} width={104} height={67} /><line x1={52.5} x2={52.5} y1={0.5} y2={67.5} /><circle cx={52.5} cy={34} r={9.15} />
          <rect x={0.5} y={13.8} width={16.5} height={40.3} /><rect x={88} y={13.8} width={16.5} height={40.3} />
          <rect x={0.5} y={24.8} width={5.5} height={18.3} /><rect x={99} y={24.8} width={5.5} height={18.3} />
        </g>
        {shots.map((e, i) => {
          const r = 0.9 + Math.sqrt(e.xg) * 4.2
          const fill = e.side === 'home' ? 'rgb(var(--accent))' : '#B4BEC9'
          return (<g key={i}><circle cx={e.x} cy={e.y} r={r} fill={fill} fillOpacity={e.goal ? 0.95 : 0.4} stroke={e.goal ? '#fff' : fill} strokeWidth={e.goal ? 0.7 : 0.3}><title>{`${e.minute}' ${e.player} - xG ${e.xg}${e.goal ? ' GOAL' : e.sot ? ' (on target)' : ''}`}</title></circle></g>)
        })}
      </svg>
      <figcaption className="mt-1 flex flex-wrap justify-center gap-x-4 text-[11px] text-fog-500">
        <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-accent align-middle" />{home} (attacks right)</span><span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-fog-300 align-middle" />{away}</span><span>size = xG · outlined = goal</span>
      </figcaption>
    </figure>
  )
}

export function XgTimeline({ timeline, step, events }: { timeline: St[]; step: number; events: Ev[] }) {
  const data = timeline.slice(0, step + 1).map((s) => ({ minute: s.minute, home: s.home_xg, away: s.away_xg }))
  const goals = events.filter((e) => e.type === 'shot' && e.goal && e.minute <= timeline[step].minute)
  const at = (m: number, side: string) => { const s = [...data].reverse().find((d) => d.minute <= m); return s ? (side === 'home' ? s.home : s.away) : 0 }
  return (
    <div role="img" aria-label="Cumulative expected goals by team">
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          <CartesianGrid stroke="#243040" strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="minute" type="number" domain={[0, 90]} ticks={[0, 15, 30, 45, 60, 75, 90]} stroke="#334357" /><YAxis stroke="#334357" />
          <Line dataKey="home" name="Home xG" stroke="rgb(var(--accent))" strokeWidth={2.2} dot={false} isAnimationActive={false} type="stepAfter" />
          <Line dataKey="away" name="Away xG" stroke="#B4BEC9" strokeWidth={2.2} dot={false} isAnimationActive={false} type="stepAfter" />
          {goals.map((g, i) => <ReferenceDot key={i} x={g.minute} y={at(g.minute, g.side)} r={4.5} fill={g.side === 'home' ? 'rgb(var(--accent))' : '#B4BEC9'} stroke="#fff" />)}
          <Tooltip contentStyle={tip} />
        </LineChart>
      </ResponsiveContainer>
      <p className="text-center text-[11px] text-fog-500">White-ringed dots are goals</p>
    </div>
  )
}
