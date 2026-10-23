import { Bar, BarChart, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useState } from 'react'
import { signed } from '../../lib/format'
import type { Explanation } from '../../lib/types'
import { Pill, Segmented } from '../ui'

/** "Why?" panel: plain-language factors for everyone, Shapley table for students and researchers. */
export function ExplainPanel({ ex, outcomes, onClass }: { ex: Explanation; outcomes?: { label: string; cls: number }[]; onClass?: (c: number) => void }) {
  const [mode, setMode] = useState<'simple' | 'technical'>('simple')
  const rows = ex.contributions.filter((r) => Math.abs(r.contribution_pp) >= 0.15).slice(0, 10)
  return (
    <div className="space-y-3" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="text-xs text-fog-500">Explaining</div>
          <div className="text-lg font-semibold">{ex.simple.headline}</div>
        </div>
        <div className="flex items-center gap-2">
          {outcomes && onClass && outcomes.length > 2 && <Segmented label="Outcome to explain" value={String(ex.target_class)} onChange={(v) => onClass(+v)} options={outcomes.map((o) => ({ value: String(o.cls), label: o.label }))} />}
          <Segmented label="Explanation level" value={mode} onChange={setMode} options={[{ value: 'simple', label: 'Simple' }, { value: 'technical', label: 'Technical' }]} />
        </div>
      </div>
      {mode === 'simple' ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <h4 className="mb-1 text-xs font-medium text-up">Helping</h4>
            {ex.simple.positives.length ? <ul className="space-y-1.5 text-sm">{ex.simple.positives.map((p, i) => <li key={i} className="flex gap-2"><span className="num w-14 shrink-0 text-up">{signed(p.pp)}</span>{p.text}</li>)}</ul> : <p className="text-sm text-fog-500">No strong supporting factors.</p>}
          </div>
          <div>
            <h4 className="mb-1 text-xs font-medium text-down">Hurting</h4>
            {ex.simple.negatives.length ? <ul className="space-y-1.5 text-sm">{ex.simple.negatives.map((p, i) => <li key={i} className="flex gap-2"><span className="num w-14 shrink-0 text-down">{signed(p.pp)}</span>{p.text}</li>)}</ul> : <p className="text-sm text-fog-500">No strong opposing factors.</p>}
          </div>
          <p className="text-xs text-fog-500 sm:col-span-2">{ex.simple.baseline_text} Numbers are percentage points (pp) of win probability.</p>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-xs leading-relaxed text-fog-500">{ex.technical.method} <Pill tone="model">{ex.technical.model}</Pill></p>
          <div className="overflow-x-auto scroll-thin">
            <table className="w-full min-w-[520px] text-left text-xs">
              <thead className="text-fog-500"><tr><th className="py-1 font-medium">Feature</th><th className="font-medium">Value</th><th className="font-medium">Training mean</th><th className="text-right font-medium">Contribution</th></tr></thead>
              <tbody className="divide-y divide-ink-700">
                {ex.technical.table.map((r) => (
                  <tr key={r.feature}><td className="py-1.5">{r.label} <span className="num text-fog-600">{r.feature}</span></td><td className="num">{r.value_text}</td><td className="num text-fog-500">{r.reference != null ? r.reference.toFixed(2) : '–'}</td>
                    <td className={`num text-right font-semibold ${r.contribution_pp > 0 ? 'text-up' : r.contribution_pp < 0 ? 'text-down' : 'text-fog-500'}`}>{signed(r.contribution_pp, 2)} pp</td></tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="num text-[11px] text-fog-600">baseline {(ex.base_value * 100).toFixed(1)}% + Σ contributions = {(ex.probability * 100).toFixed(1)}% (additivity gap {ex.technical.additivity_gap_pp} pp)</p>
        </div>
      )}
      <div role="img" aria-label="Contribution of each factor in percentage points">
        <ResponsiveContainer width="100%" height={Math.max(120, rows.length * 24 + 24)}>
          <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 0 }}>
            <XAxis type="number" tickFormatter={(v) => `${v}`} stroke="#334357" />
            <YAxis type="category" dataKey="label" width={170} stroke="#334357" tick={{ fontSize: 11 }} />
            <ReferenceLine x={0} stroke="#66737F" />
            <Tooltip cursor={{ fill: '#18222B' }} contentStyle={{ background: '#121A21', border: '1px solid #243040', borderRadius: 8, fontSize: 12 }} formatter={(v: any) => [`${signed(v, 2)} pp`, 'Contribution']} />
            <Bar dataKey="contribution_pp" radius={2} isAnimationActive={false}>{rows.map((r) => <Cell key={r.feature} fill={r.contribution_pp >= 0 ? '#5FD39A' : '#F0646E'} />)}</Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
