import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Series } from '../../lib/types'

export function MomentumChart({ series, step, onStep, height = 160 }: { series: Series; step: number; onStep?: (k: number) => void; height?: number }) {
  const data = series.steps.map((s) => ({ i: s.i, m: s.momentum }))
  return (
    <div role="img" aria-label="Momentum score over the match, 50 is balanced">
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 6, right: 12, bottom: 0, left: -18 }} onClick={(e: any) => { if (onStep && e?.activeTooltipIndex != null) onStep(e.activeTooltipIndex) }}>
          <defs><linearGradient id="mom" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="rgb(var(--accent))" stopOpacity={0.45} /><stop offset="100%" stopColor="rgb(var(--accent))" stopOpacity={0.02} /></linearGradient></defs>
          <CartesianGrid stroke="#243040" strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="i" tickFormatter={(i) => String(series.steps[i]?.label ?? '').replace(/^Inn \d · /, '')} interval="preserveStartEnd" minTickGap={28} stroke="#334357" />
          <YAxis domain={[0, 100]} ticks={[0, 50, 100]} stroke="#334357" />
          <ReferenceLine y={50} stroke="#334357" />
          <ReferenceLine x={step} stroke="rgb(var(--accent))" strokeWidth={1.5} />
          <Area dataKey="m" stroke="rgb(var(--accent))" strokeWidth={2} fill="url(#mom)" isAnimationActive={false} name="Momentum" />
          <Tooltip contentStyle={{ background: '#121A21', border: '1px solid #243040', borderRadius: 8, fontSize: 12 }} labelFormatter={(i) => series.steps[i as number]?.label} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
