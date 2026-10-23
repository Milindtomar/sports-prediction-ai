import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Series } from '../../lib/types'

const COLORS = ['rgb(var(--accent))', '#B4BEC9', '#F0646E']

/** Win-probability trace with a bootstrap uncertainty band; click a point to jump the replay there. */
export function WinProbChart({ series, step, onStep, height = 230, labels }: {
  series: Series; step: number; onStep?: (k: number) => void; height?: number; labels: string[]
}) {
  const multi = series.classes.length === 3
  const data = series.steps.map((s) => {
    const row: Record<string, number | string> = { i: s.i, label: s.label }
    if (multi) s.probs.forEach((p, c) => { row[`p${c}`] = +(p * 100).toFixed(1) })
    else { const c = series.focus_class; row.p = +(s.probs[c] * 100).toFixed(1); row.band = [+(s.lo[c] * 100).toFixed(1), +(s.hi[c] * 100).toFixed(1)] as unknown as number }
    return row
  })
  return (
    <div role="img" aria-label={`Win probability over the match. ${labels.join(' / ')}`}>
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -18 }} onClick={(e: any) => { if (onStep && e?.activeTooltipIndex != null) onStep(e.activeTooltipIndex) }}>
          <CartesianGrid stroke="#243040" strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="i" tickFormatter={(i) => String(series.steps[i]?.label ?? '').replace(/^Inn \d · /, '')} interval="preserveStartEnd" minTickGap={28} stroke="#334357" />
          <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickFormatter={(v) => `${v}%`} stroke="#334357" />
          <ReferenceLine y={50} stroke="#334357" />
          <ReferenceLine x={step} stroke="rgb(var(--accent))" strokeWidth={1.5} />
          {!multi && <Area dataKey="band" stroke="none" fill="rgb(var(--accent))" fillOpacity={0.16} isAnimationActive={false} />}
          {!multi && <Line dataKey="p" stroke="rgb(var(--accent))" strokeWidth={2.2} dot={false} isAnimationActive={false} name={labels[1]} />}
          {multi && [0, 1, 2].map((c) => <Line key={c} dataKey={`p${c}`} stroke={COLORS[c]} strokeWidth={c === 1 ? 1.5 : 2.2} strokeDasharray={c === 1 ? '4 3' : undefined} dot={false} isAnimationActive={false} name={labels[c]} />)}
          <Tooltip contentStyle={{ background: '#121A21', border: '1px solid #243040', borderRadius: 8, fontSize: 12 }} labelFormatter={(i) => series.steps[i as number]?.label} formatter={(v: any, n: any) => (Array.isArray(v) ? [`${v[0]}–${v[1]}%`, 'model band'] : [`${v}%`, n])} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
