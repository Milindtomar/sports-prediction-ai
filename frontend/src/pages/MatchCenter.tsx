import { AnimatePresence, motion } from 'framer-motion'
import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { WinProbChart } from '../components/charts/WinProbChart'
import { MomentumChart } from '../components/charts/MomentumChart'
import { TimelineControls } from '../components/match/Controls'
import { CoachCard } from '../components/match/CoachCard'
import { InsightsCard, KeyPlayersCard, MomentumCard, ScoreHeader, WinProbCard } from '../components/match/Cards'
import { ExplainPanel } from '../components/match/ExplainPanel'
import { EmptyState, ErrorState, Loading, Panel, Skeleton } from '../components/ui'
import { useMatch } from '../lib/MatchContext'
import { SportPanels } from '../sports/SportPanels'

export default function MatchCenter() {
  const { sport, matches, match, series, step, setStep, analysis, state, targetClass, setTargetClass } = useMatch()
  const [why, setWhy] = useState(false)
  const whyRef = useRef<HTMLDivElement>(null)
  const a = analysis.data

  if (matches.error) return <ErrorState error={matches.error} onRetry={matches.reload} title="Matches could not load" />
  if (matches.data && matches.data.length === 0) return <EmptyState title="No matches available" hint="Run `python -m app.seed` on the backend to create the demo matches." />

  return (
    <div className="space-y-3">
      <TimelineControls />
      {match.error && <ErrorState error={match.error} onRetry={match.reload} />}
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="min-w-0 space-y-3">
          {a ? <ScoreHeader a={a} title={match.data?.title} /> : <Skeleton className="h-36" />}
          <Panel title="Win probability through the match" subtitle="Line = model estimate, shaded band = disagreement across a bootstrap ensemble. Click the chart to jump.">
            {series.error ? <ErrorState error={series.error} onRetry={series.reload} /> : !series.data ? <Loading label="Computing predictions for every step" height="h-56" /> :
              <WinProbChart series={series.data} step={step} onStep={setStep} labels={a?.outcomes.map((o) => o.label) ?? series.data.classes} />}
          </Panel>
          <AnimatePresence initial={false}>
            {why && (
              <motion.div ref={whyRef} initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
                <Panel title="Why this prediction?" subtitle="Every number below is computed from the current match state" actions={<button className="text-xs text-fog-500 hover:text-fog-100" onClick={() => setWhy(false)}>Close</button>}>
                  {analysis.error ? <ErrorState error={analysis.error} onRetry={analysis.reload} /> : a?.explanation ? <ExplainPanel ex={a.explanation} outcomes={a.outcomes} onClass={setTargetClass} /> :
                    a?.terminal ? <p className="text-sm text-fog-500">The match is decided, so there is nothing left to explain.</p> : <Loading />}
                </Panel>
              </motion.div>
            )}
          </AnimatePresence>
          <Panel title="Momentum through the match" subtitle="50 = balanced. Above 50 favours the named side.">
            {series.data ? <MomentumChart series={series.data} step={step} onStep={setStep} /> : <Loading height="h-32" />}
          </Panel>
          {match.data ? <SportPanels sport={sport} detail={match.data} step={step} /> : <Skeleton className="h-64" />}
        </div>
        <aside className="space-y-3" aria-label="Match intelligence">
          {analysis.error && !a && <ErrorState error={analysis.error} onRetry={analysis.reload} title="Prediction unavailable" />}
          {a ? (
            <div className={analysis.loading ? 'space-y-3 opacity-70 transition-opacity' : 'space-y-3 transition-opacity'}>
              <WinProbCard a={a} whyOpen={why} onWhy={() => { setWhy(true); setTimeout(() => whyRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 60) }} />
              <Link to={`/app/${sport}/simulate`} className="flex items-center justify-between rounded-md border hairline bg-ink-900 px-3 py-2 text-sm hover:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent">
                <span>Test a what-if in the Simulation Lab</span><span aria-hidden>›</span>
              </Link>
              <MomentumCard m={a.momentum} />
              <KeyPlayersCard players={a.key_players} />
              <InsightsCard items={a.insights} />
              {a && sport && <CoachCard sport={sport} state={state} teams={sport === 'cricket' ? undefined : [a.scoreboard.teams[0].name, a.scoreboard.teams[1].name]} />}
            </div>
          ) : !analysis.error && <><Skeleton className="h-52" /><Skeleton className="h-40" /><Skeleton className="h-40" /></>}
        </aside>
      </div>
      {targetClass != null && <p className="text-xs text-fog-600">Explaining outcome index {targetClass}.</p>}
    </div>
  )
}
