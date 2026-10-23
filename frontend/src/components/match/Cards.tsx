import { motion } from 'framer-motion'
import { HelpCircle } from 'lucide-react'
import { ReactNode } from 'react'
import { cn, pct } from '../../lib/format'
import type { Analysis, KeyPlayer, Momentum } from '../../lib/types'
import { AnimatedNumber, Btn, Disclaimer, Pill } from '../ui'

export function ScoreHeader({ a, title }: { a: Analysis; title?: string }) {
  const sb = a.scoreboard
  return (
    <div className="rounded-lg border hairline bg-ink-900 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-fog-500">
        <span>{title ?? sb.venue}</span>
        <span className="flex items-center gap-2"><Pill tone="live">{sb.clock}</Pill><span>{sb.phase}</span></span>
      </div>
      <div className="mt-3 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        {sb.teams.map((t, i) => (
          <div key={t.name} className={cn(i === 1 ? 'order-3 text-right' : 'order-1')}>
            <div className="truncate text-sm text-fog-300">{t.name}</div>
            <div className="num text-3xl font-semibold leading-tight sm:text-4xl">{t.score}</div>
            <div className="text-xs text-fog-500">{t.sub}</div>
          </div>
        ))}
        <div className="order-2 text-xs text-fog-600" aria-hidden>vs</div>
      </div>
      <p className="mt-3 text-sm font-medium text-accent">{sb.status}</p>
    </div>
  )
}

export function WinProbCard({ a, onWhy, whyOpen }: { a: Analysis; onWhy?: () => void; whyOpen?: boolean }) {
  const h = a.headline
  const multi = a.outcomes.length === 3
  return (
    <div className="rounded-lg border hairline bg-ink-900 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Win probability</h3>
        <Pill tone="model">MODEL PREDICTION</Pill>
      </div>
      {!multi ? (
        <div className="mt-3">
          <div className="text-xs text-fog-500">{h.label}</div>
          <div className="flex items-baseline gap-3">
            <AnimatedNumber value={h.prob * 100} format={(v) => `${v.toFixed(0)}%`} className="num text-5xl font-semibold leading-none" />
            {!a.terminal && <span className="num text-xs text-fog-500" title="10th–90th percentile across a bootstrap ensemble of models">model range {pct(h.lo)}–{pct(h.hi)}</span>}
            {a.terminal && <Pill tone="warn">Result decided</Pill>}
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded bg-ink-800" aria-hidden>
            <motion.div className="h-full bg-accent" initial={false} animate={{ width: `${h.prob * 100}%` }} transition={{ duration: 0.45 }} />
          </div>
          <div className="mt-1 flex justify-between text-xs text-fog-500"><span>{h.label} {pct(h.prob)}</span><span>{a.outcomes[1 - a.focus.cls].label} {pct(1 - h.prob)}</span></div>
        </div>
      ) : (
        <div className="mt-3 space-y-2.5">
          {a.outcomes.map((o) => (
            <div key={o.cls}>
              <div className="flex items-baseline justify-between text-sm"><span className="text-fog-300">{o.label}</span>
                <span className="num text-lg font-semibold"><AnimatedNumber value={o.prob * 100} format={(v) => `${v.toFixed(0)}%`} /></span></div>
              <div className="mt-1 h-2 overflow-hidden rounded bg-ink-800" aria-hidden><motion.div className="h-full" style={{ background: ['rgb(var(--accent))', '#B4BEC9', '#F0646E'][o.cls] }} initial={false} animate={{ width: `${o.prob * 100}%` }} transition={{ duration: 0.45 }} /></div>
              {!a.terminal && <div className="num mt-0.5 text-[11px] text-fog-600">model range {pct(o.lo)}–{pct(o.hi)}</div>}
            </div>
          ))}
        </div>
      )}
      <div className="mt-4 flex items-center gap-2">
        {onWhy && !a.terminal && <Btn onClick={onWhy} aria-expanded={whyOpen}><HelpCircle className="h-4 w-4" aria-hidden /> Why?</Btn>}
      </div>
      <div className="mt-3"><Disclaimer>{a.disclaimer}</Disclaimer></div>
    </div>
  )
}

export function MomentumCard({ m, compact }: { m: Momentum; compact?: boolean }) {
  const tone = m.score >= 60 ? 'text-up' : m.score <= 40 ? 'text-down' : 'text-fog-300'
  return (
    <div className="rounded-lg border hairline bg-ink-900 p-4">
      <div className="flex items-center justify-between"><h3 className="text-sm font-semibold">Momentum · {m.side}</h3></div>
      <div className="mt-2 flex items-baseline gap-2">
        <AnimatedNumber value={m.score} format={(v) => v.toFixed(0)} className="num text-4xl font-semibold" /><span className="num text-sm text-fog-500">/100</span>
        <span className={cn('text-sm font-medium', tone)}>{m.label}</span>
      </div>
      <div className="relative mt-3 h-2 rounded bg-ink-800" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={m.score} aria-label="Momentum">
        <div className="absolute left-1/2 top-[-3px] h-[14px] w-px bg-ink-600" aria-hidden />
        <motion.div className="absolute top-0 h-full rounded" style={{ background: m.score >= 50 ? '#5FD39A' : '#F0646E' }} initial={false}
          animate={{ left: m.score >= 50 ? '50%' : `${m.score}%`, width: `${Math.abs(m.score - 50)}%` }} transition={{ duration: 0.45 }} />
      </div>
      {!compact && (
        <>
          <p className="mt-3 text-xs font-medium text-fog-300">Main factors</p>
          <ul className="mt-1 space-y-1">
            {m.factors.slice(0, 4).map((f) => (
              <li key={f.label} className="flex items-start gap-2 text-xs">
                <span className={cn('num w-12 shrink-0 text-right font-semibold', f.direction === 'positive' ? 'text-up' : f.direction === 'negative' ? 'text-down' : 'text-fog-500')}>{f.points >= 0 ? '+' : '−'}{Math.abs(f.points).toFixed(1)}</span>
                <span><span className="text-fog-100">{f.label}</span> <span className="text-fog-500">- {f.detail}</span></span>
              </li>
            ))}
          </ul>
          <details className="mt-3 text-xs text-fog-500"><summary className="cursor-pointer text-fog-300">How is momentum calculated?</summary><p className="mt-1 leading-relaxed">{m.formula}</p></details>
        </>
      )}
    </div>
  )
}

export function InsightsCard({ items }: { items: string[] }) {
  return (
    <div className="rounded-lg border hairline bg-ink-900 p-4">
      <h3 className="text-sm font-semibold">AI insights</h3>
      <ul className="mt-2 space-y-2 text-sm text-fog-300">{items.map((t, i) => <li key={i} className="flex gap-2"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent" aria-hidden />{t}</li>)}</ul>
    </div>
  )
}

export function KeyPlayersCard({ players }: { players: KeyPlayer[] | undefined }) {
  return (
    <div className="rounded-lg border hairline bg-ink-900 p-4">
      <h3 className="text-sm font-semibold">Key players</h3>
      <p className="text-[11px] text-fog-600">ACTUAL RESULT so far in this replay</p>
      {!players?.length ? <p className="py-4 text-sm text-fog-500">No player events yet at this point of the match.</p> : (
        <ul className="mt-2 divide-y divide-ink-700">
          {players.map((p) => (
            <li key={p.name + p.role} className="flex items-center justify-between gap-3 py-2">
              <div className="min-w-0"><div className="truncate text-sm">{p.name}</div><div className="truncate text-xs text-fog-500">{p.team} · {p.role}</div></div>
              <div className="text-right"><div className="num text-sm font-semibold">{p.headline}</div><div className="text-[11px] text-fog-500">{p.detail}</div></div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function Section({ children, cols = 'lg:grid-cols-3' }: { children: ReactNode; cols?: string }) {
  return <div className={cn('grid grid-cols-1 gap-3', cols)}>{children}</div>
}
