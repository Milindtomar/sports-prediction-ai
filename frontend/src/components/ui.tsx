import { animate, motion, useMotionValue, useTransform } from 'framer-motion'
import { AlertTriangle, Inbox, Loader2, RefreshCw } from 'lucide-react'
import { ReactNode, useEffect } from 'react'
import { cn } from '../lib/format'

export function Panel({ title, subtitle, actions, children, className, pad = true, id }: {
  title?: ReactNode; subtitle?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string; pad?: boolean; id?: string
}) {
  return (
    <section id={id} className={cn('rounded-lg border hairline bg-ink-900', className)}>
      {(title || actions) && (
        <header className="flex items-start justify-between gap-3 border-b hairline px-4 py-3">
          <div className="min-w-0">
            {title && <h2 className="text-sm font-semibold tracking-tight text-fog-100">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-fog-500">{subtitle}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={pad ? 'p-4' : ''}>{children}</div>
    </section>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn('animate-pulse rounded bg-ink-800', className)} />
}

export function Loading({ label = 'Loading', height = 'h-40' }: { label?: string; height?: string }) {
  return (
    <div role="status" aria-live="polite" className={cn('flex items-center justify-center gap-2 text-sm text-fog-500', height)}>
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> {label}…
    </div>
  )
}

export function ErrorState({ error, onRetry, title = 'This section could not load' }: { error: Error | null; onRetry?: () => void; title?: string }) {
  return (
    <div role="alert" className="flex flex-col items-start gap-2 rounded-md border border-down/40 bg-down/5 p-4 text-sm">
      <div className="flex items-center gap-2 font-medium text-down"><AlertTriangle className="h-4 w-4" aria-hidden /> {title}</div>
      <p className="text-fog-300">{error?.message ?? 'Unknown error.'}</p>
      {onRetry && <Btn onClick={onRetry} variant="ghost"><RefreshCw className="h-3.5 w-3.5" aria-hidden /> Retry</Btn>}
    </div>
  )
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 py-10 text-center">
      <Inbox className="h-6 w-6 text-fog-600" aria-hidden />
      <p className="text-sm font-medium text-fog-300">{title}</p>
      {hint && <p className="max-w-sm text-xs text-fog-500">{hint}</p>}
      {action}
    </div>
  )
}

type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'solid' | 'ghost' | 'quiet' }
export function Btn({ variant = 'solid', className, ...p }: BtnProps) {
  const base = 'inline-flex items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-45'
  const v = {
    solid: 'bg-accent text-ink-950 hover:brightness-110',
    ghost: 'border hairline text-fog-100 hover:bg-ink-800',
    quiet: 'text-fog-300 hover:bg-ink-800 hover:text-fog-100',
  }[variant]
  return <button type="button" className={cn(base, v, className)} {...p} />
}

export function Segmented<T extends string>({ value, onChange, options, label }: {
  value: T; onChange: (v: T) => void; options: { value: T; label: ReactNode }[]; label: string
}) {
  return (
    <div role="tablist" aria-label={label} className="inline-flex rounded-md border hairline bg-ink-950 p-0.5">
      {options.map((o) => (
        <button key={o.value} role="tab" aria-selected={value === o.value} onClick={() => onChange(o.value)}
          className={cn('rounded px-2.5 py-1 text-xs font-medium transition-colors', value === o.value ? 'bg-ink-700 text-fog-100' : 'text-fog-500 hover:text-fog-100')}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

/** Always-visible reminder that nothing in the app is a live sports feed. */
export function DemoBadge({ className = '' }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded border border-warn/50 px-2 py-0.5 text-[11px] font-medium text-warn ${className}`}
      title="All matches, players and statistics are simulated. Predictions are model estimates, not live forecasts.">
      <span className="h-1.5 w-1.5 rounded-full bg-warn" aria-hidden /> SYNTHETIC DEMO DATA
    </span>
  )
}

export function Pill({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'live' | 'model' | 'up' | 'down' | 'warn' }) {
  const t = {
    neutral: 'border-ink-600 text-fog-300', live: 'border-accent/50 text-accent', model: 'border-model/40 text-model',
    up: 'border-up/40 text-up', down: 'border-down/40 text-down', warn: 'border-warn/40 text-warn',
  }[tone]
  return <span className={cn('inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium', t)}>{children}</span>
}

export function LiveDot({ label = 'Simulated replay' }: { label?: string }) {
  return <span className="inline-flex items-center gap-1.5 text-xs text-fog-300"><span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-accent" aria-hidden />{label}</span>
}

/** Number that eases to its new value so changes are noticed without being distracting. */
export function AnimatedNumber({ value, format, className }: { value: number; format: (v: number) => string; className?: string }) {
  const mv = useMotionValue(value)
  const text = useTransform(mv, (v) => format(v))
  useEffect(() => { const c = animate(mv, value, { duration: 0.45, ease: 'easeOut' }); return () => c.stop() }, [value, mv])
  return <motion.span className={className} aria-label={format(value)}>{text}</motion.span>
}

export function Kv({ k, v }: { k: ReactNode; v: ReactNode }) {
  return <div className="flex items-baseline justify-between gap-3 py-1 text-sm"><dt className="text-fog-500">{k}</dt><dd className="num text-right text-fog-100">{v}</dd></div>
}

export function Disclaimer({ children }: { children: ReactNode }) {
  return <p className="rounded border border-model/25 bg-model/5 px-2.5 py-1.5 text-[11px] leading-snug text-model">{children}</p>
}
