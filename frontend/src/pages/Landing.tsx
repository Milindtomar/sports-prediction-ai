import { ArrowRight, Brain, FlaskConical, Gauge, ShieldCheck } from 'lucide-react'
import { motion } from 'framer-motion'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Footer, Logo } from '../components/Shell'
import { Btn, DemoBadge } from '../components/ui'
import { api } from '../lib/api'
import { cn, pct, pp } from '../lib/format'
import { useAsync } from '../lib/hooks'
import type { Analysis, SimResult } from '../lib/types'

function LiveWhatIf() {
  const base = useAsync<{ a: Analysis; events: { id: string; label: string }[] }>(async () => {
    const [state, meta] = await Promise.all([api.defaultState('cricket'), api.meta('cricket')])
    return { a: await api.predict('cricket', state), events: meta.events.slice(0, 4) }
  }, [])
  const [sim, setSim] = useState<SimResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)

  if (base.error)
    return <div className="rounded-lg border hairline p-5 text-sm text-fog-300" role="status">The live demo needs the API running. Start the backend (see README), then reload. Everything else on this page still works.</div>
  if (!base.data) return <div className="h-56 animate-pulse rounded-lg bg-ink-800" aria-label="Loading live demo" />
  const { a, events } = base.data
  const run = async (id: string) => {
    setBusy(true); setFailed(false)
    try { setSim(await api.simulate('cricket', a.state, [{ id }])) } catch { setFailed(true) } finally { setBusy(false) }
  }
  const d = sim?.deltas[sim.focus_class]
  return (
    <div className="rounded-lg border hairline bg-ink-900 p-5">
      <p className="text-xs text-fog-500">{a.scoreboard.teams.map((t) => `${t.name} ${t.score}`).join(' vs ')} · {a.scoreboard.status}</p>
      <p className="mt-2 text-sm text-fog-300">{a.headline.label} win probability</p>
      <p className="num text-6xl font-semibold tracking-tight">{pct(d ? d.after : a.headline.prob)}</p>
      <p className={cn('num h-5 text-sm', d && (d.delta_pp >= 0 ? 'text-up' : 'text-down'))} aria-live="polite">{d ? `${pp(d.delta_pp)} after “${sim!.applied[0].label}”` : ''}</p>
      <p className="mb-2 mt-4 text-sm font-medium">What if the next ball is…</p>
      <div className="flex flex-wrap gap-2">
        {events.map((e) => <button key={e.id} disabled={busy} onClick={() => run(e.id)} className="rounded-md border hairline bg-ink-950 px-3 py-1.5 text-sm hover:border-accent hover:text-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-50">{e.label}</button>)}
      </div>
      {failed && <p className="mt-2 text-sm text-down" role="alert">That simulation failed. Try again.</p>}
      <p className="mt-3 text-xs text-fog-500">This calls the real model through the API. It re-computes features and the prediction. Nothing is pre-written.</p>
    </div>
  )
}

/** One line, drawn once: the model's win probability at every over of a real (simulated) demo match from the API. */
function LiveTrace() {
  const t = useAsync(async () => {
    const ms = await api.matches('cricket')
    if (!ms.length) return null
    const s = await api.series(ms[0].id)
    return { title: ms[0].title, pts: s.steps.map((x) => x.probs[s.focus_class] as number) }
  }, [])
  if (!t.data) return null
  const { pts, title } = t.data
  const W = 520, H = 90, x = (i: number) => (i / Math.max(pts.length - 1, 1)) * W, y = (p: number) => H - p * H
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(p).toFixed(1)}`).join(' ')
  return (
    <figure className="mt-8 max-w-lg" aria-label={`Win probability through ${title}, drawn from the API`}>
      <svg viewBox={`0 0 ${W} ${H}`} className="h-24 w-full overflow-visible" role="img" aria-label="Win probability line for a simulated cricket match">
        <line x1="0" x2={W} y1={H / 2} y2={H / 2} stroke="#243040" strokeDasharray="3 4" />
        <motion.path d={d} fill="none" stroke="rgb(var(--accent))" strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round"
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 2.2, ease: 'easeInOut' }} />
      </svg>
      <figcaption className="mt-1 text-xs text-fog-500">Model win probability over a simulated match ({title}). Real model output, not an illustration.</figcaption>
    </figure>
  )
}

const FEATURES = [
  { icon: Gauge, t: 'Win probability and momentum', d: 'Calibrated probabilities with an uncertainty band, and a 0–100 momentum score you can break down into its parts.' },
  { icon: Brain, t: 'Explanations at two depths', d: 'Plain-language reasons for fans, and per-feature contributions for analysts. Contributions add up to the prediction.' },
  { icon: FlaskConical, t: 'Simulation Lab', d: 'Change the match state, run the pipeline again, and see exactly which factors moved the probability.' },
  { icon: ShieldCheck, t: 'Honest by design', d: 'Trained on reproducible synthetic data, evaluated chronologically, and labelled as such everywhere in the interface.' },
]

export default function Landing() {
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4"><Logo /><nav className="flex items-center gap-4 text-sm text-fog-300"><DemoBadge className="hidden sm:inline-flex" /><Link to="/models" className="hover:text-fog-100">Model Insights</Link><Link to="/hci" className="hover:text-fog-100">HCI Study</Link></nav></header>
      <main>
        <section className="mx-auto grid max-w-6xl gap-8 px-4 pb-14 pt-8 lg:grid-cols-2 lg:items-center lg:pt-14">
          <div>
            <h1 className="max-w-xl text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">Ask a match what would change the result.</h1>
            <p className="mt-4 max-w-lg text-fog-300">SPORTS AI predicts who is winning in cricket, football and basketball, explains why, and lets you test a wicket, a goal or a three-pointer before it happens.</p>
            <div className="mt-6 flex flex-wrap gap-3"><Link to="/sports"><Btn>Enter Analytics <ArrowRight className="h-4 w-4" aria-hidden /></Btn></Link><Link to="/app/cricket/match"><Btn variant="ghost">Open a demo cricket match</Btn></Link></div>
            <LiveTrace />
          </div>
          <LiveWhatIf />
        </section>
        <section className="border-t hairline">
          <div className="mx-auto grid max-w-6xl gap-6 px-4 py-12 sm:grid-cols-2">
            {FEATURES.map((f) => <div key={f.t} className="flex gap-3"><f.icon className="mt-0.5 h-5 w-5 shrink-0 text-accent" aria-hidden /><div><h2 className="font-medium">{f.t}</h2><p className="mt-1 text-sm text-fog-300">{f.d}</p></div></div>)}
          </div>
        </section>
        <section className="border-t hairline">
          <div className="mx-auto max-w-6xl px-4 py-10 text-sm text-fog-300"><p className="max-w-2xl">All matches, players and statistics are simulated and all team and player names are fictional. Predictions are model outputs, and the AI Coach gives AI-assisted recommendations. It does not make decisions for anyone.</p></div>
        </section>
      </main>
      <Footer />
    </div>
  )
}
