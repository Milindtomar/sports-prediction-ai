import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { SportIcon } from '../components/SportIcon'
import { Footer, Logo } from '../components/Shell'
import { DemoBadge, EmptyState, ErrorState, Loading } from '../components/ui'
import { api } from '../lib/api'
import { pct } from '../lib/format'
import { useAsync } from '../lib/hooks'

export default function SportSelect() {
  const s = useAsync(() => api.sports(), [])
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4"><Logo /><DemoBadge /></header>
      <main className="mx-auto max-w-6xl px-4 pb-16 pt-6">
        <h1 className="text-2xl font-semibold tracking-tight">Choose a sport</h1>
        <p className="mt-1 text-sm text-fog-300">Each sport has its own model, features and what-if events. The workspace is the same.</p>
        <div className="mt-6">
          {s.error ? <ErrorState error={s.error} onRetry={s.reload} title="Could not load sports" />
            : !s.data ? <Loading />
            : !s.data.length ? <EmptyState title="No sports available" hint="Check that the backend has started and models are trained." />
            : <ul className="grid gap-4 md:grid-cols-3">{s.data.map((x, i) => (
                <motion.li key={x.key} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }} data-sport={x.key}>
                  <Link to={`/app/${x.key}/match`} className="block h-full rounded-lg border hairline bg-ink-900 p-5 transition-colors hover:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent">
                    <div className="flex items-start justify-between"><SportIcon sport={x.key} className="h-8 w-8 text-accent" /><span className="rounded border hairline px-1.5 py-0.5 text-[11px] text-fog-500">{x.status === 'ready' ? 'Demo data · model ready' : `Demo data · ${x.status}`}</span></div>
                    <h2 className="mt-3 text-lg font-semibold">{x.name}</h2>
                    <p className="mt-1 text-sm text-fog-300">{x.tagline}</p>
                    <ul className="mt-3 space-y-1 text-xs text-fog-500">{x.analytics.map((a) => <li key={a}>{a}</li>)}</ul>
                    {x.model && <p className="num mt-4 text-xs text-fog-500">{x.model.name} · accuracy {pct(x.model.accuracy)} · AUC {x.model.roc_auc.toFixed(2)} on held-out synthetic matches</p>}
                  </Link>
                </motion.li>))}</ul>}
        </div>
      </main>
      <Footer />
    </div>
  )
}
