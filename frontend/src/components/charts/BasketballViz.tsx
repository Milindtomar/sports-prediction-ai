import { useState } from 'react'
import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Segmented } from '../ui'

type Ev = Record<string, any>
type St = Record<string, any>
const tip = { background: '#121A21', border: '1px solid #243040', borderRadius: 8, fontSize: 12 }

export function ScoreProgressionBB({ timeline, step }: { timeline: St[]; step: number }) {
  const data = timeline.slice(0, step + 1).map((s) => ({ min: +(s.elapsed_sec / 60).toFixed(1), home: s.home_score, away: s.away_score, margin: s.home_score - s.away_score }))
  return (
    <div role="img" aria-label="Score progression and margin">
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: -14, bottom: 0 }}>
          <CartesianGrid stroke="#243040" strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="min" type="number" domain={[0, 48]} ticks={[0, 12, 24, 36, 48]} stroke="#334357" /><YAxis stroke="#334357" />
          {[12, 24, 36].map((q) => <ReferenceLine key={q} x={q} stroke="#243040" />)}
          <Area dataKey="margin" name="Home margin" stroke="none" fill="#334357" fillOpacity={0.35} isAnimationActive={false} />
          <Line dataKey="home" name="Home" stroke="rgb(var(--accent))" strokeWidth={2.2} dot={false} isAnimationActive={false} />
          <Line dataKey="away" name="Away" stroke="#B4BEC9" strokeWidth={2.2} dot={false} isAnimationActive={false} />
          <Tooltip contentStyle={tip} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

export function CourtShotChart({ events, st, home, away }: { events: Ev[]; st: St; home: string; away: string }) {
  const [side, setSide] = useState<'both' | 'home' | 'away'>('both')
  const shots = events.filter((e) => e.type === 'shot' && e.t <= st.elapsed_sec && (side === 'both' || e.side === side))
  const made = shots.filter((s) => s.made).length
  return (
    <figure>
      <div className="mb-2 flex items-center justify-between"><Segmented label="Team filter" value={side} onChange={setSide} options={[{ value: 'both', label: 'Both' }, { value: 'home', label: home }, { value: 'away', label: away }]} />
        <span className="num text-xs text-fog-500">{made}/{shots.length} made</span></div>
      <svg viewBox="-1 -1 52 50" className="mx-auto w-full max-w-[420px] rounded border hairline bg-[#1A130C]" role="img" aria-label={`Shot chart with ${shots.length} shots`}>
        <g fill="none" stroke="#5A4630" strokeWidth={0.35}>
          <rect x={0} y={0} width={50} height={47} /><rect x={17} y={0} width={16} height={19} /><circle cx={25} cy={19} r={6} />
          <path d="M3 0 V14 A23.75 23.75 0 0 0 47 14 V0" /><circle cx={25} cy={5.25} r={0.75} stroke="#E8873C" /><line x1={22} x2={28} y1={4} y2={4} />
          <path d="M20.5 5.25 A4.5 4.5 0 0 0 29.5 5.25" />
        </g>
        {shots.map((s, i) => {
          const fill = s.side === 'home' ? 'rgb(var(--accent))' : '#B4BEC9'
          return s.made
            ? <circle key={i} cx={s.x} cy={s.y} r={1.1} fill={fill}><title>{`${s.player}: ${s.pts} pts`}</title></circle>
            : <g key={i} stroke={fill} strokeWidth={0.4} opacity={0.6}><line x1={s.x - 0.8} x2={s.x + 0.8} y1={s.y - 0.8} y2={s.y + 0.8} /><line x1={s.x - 0.8} x2={s.x + 0.8} y1={s.y + 0.8} y2={s.y - 0.8} /><title>{`${s.player}: miss`}</title></g>
        })}
      </svg>
      <figcaption className="mt-1 text-center text-[11px] text-fog-500">Filled = made, ✕ = missed · positions are illustrative (generated from shot type), not predicted</figcaption>
    </figure>
  )
}
