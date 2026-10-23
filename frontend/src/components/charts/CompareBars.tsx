import { cn } from '../../lib/format'

export interface CmpRow { label: string; a: number; b: number; fmt?: (v: number) => string; lowerBetter?: boolean }

/** Two-sided bars for team comparisons (home/left in the accent colour, away/right in neutral). */
export function CompareBars({ rows, aName, bName }: { rows: CmpRow[]; aName: string; bName: string }) {
  return (
    <div className="space-y-2.5" role="list" aria-label={`${aName} versus ${bName}`}>
      <div className="flex justify-between text-xs text-fog-500"><span className="text-accent">{aName}</span><span>{bName}</span></div>
      {rows.map((r) => {
        const tot = Math.abs(r.a) + Math.abs(r.b) || 1
        const f = r.fmt ?? ((v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1)))
        const aBetter = r.lowerBetter ? r.a < r.b : r.a > r.b
        const bBetter = r.lowerBetter ? r.b < r.a : r.b > r.a
        return (
          <div key={r.label} role="listitem">
            <div className="flex items-baseline justify-between text-xs">
              <span className={cn('num font-semibold', aBetter ? 'text-fog-100' : 'text-fog-500')}>{f(r.a)}</span>
              <span className="text-fog-500">{r.label}</span>
              <span className={cn('num font-semibold', bBetter ? 'text-fog-100' : 'text-fog-500')}>{f(r.b)}</span>
            </div>
            <div className="mt-0.5 flex h-1.5 gap-0.5" aria-hidden>
              <div className="flex flex-1 justify-end overflow-hidden rounded-l bg-ink-800"><div className="h-full" style={{ width: `${(Math.abs(r.a) / tot) * 100}%`, background: aBetter ? 'rgb(var(--accent))' : '#334357' }} /></div>
              <div className="flex-1 overflow-hidden rounded-r bg-ink-800"><div className="h-full" style={{ width: `${(Math.abs(r.b) / tot) * 100}%`, background: bBetter ? '#B4BEC9' : '#334357' }} /></div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
