import { Link } from 'react-router-dom'
import { CompareBars } from '../components/charts/CompareBars'
import { MomentumChart } from '../components/charts/MomentumChart'
import { WinProbChart } from '../components/charts/WinProbChart'
import { TimelineControls } from '../components/match/Controls'
import { KeyPlayersCard, MomentumCard } from '../components/match/Cards'
import { ExplainPanel } from '../components/match/ExplainPanel'
import { ErrorState, Loading, Panel, Kv, Pill, Disclaimer } from '../components/ui'
import { pct } from '../lib/format'
import { useMatch } from '../lib/MatchContext'
import { teamRows } from '../sports/SportPanels'

export default function AIAnalytics() {
  const { sport, analysis, series, step, setStep, state, setTargetClass } = useMatch()
  const a = analysis.data
  const t = state ? teamRows(sport, state) : null
  const m = a?.model
  return (
    <div className="space-y-3">
      <TimelineControls />
      {analysis.error && <ErrorState error={analysis.error} onRetry={analysis.reload} title="Analytics unavailable" />}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <Panel title="Predictions" subtitle="Calibrated probabilities with model-ensemble range" actions={<Pill tone="model">MODEL PREDICTION</Pill>}>
          {!a ? <Loading /> : (
            <div className="space-y-3">
              {a.outcomes.map((o) => (
                <div key={o.cls}>
                  <div className="flex justify-between text-sm"><span>{o.label}</span><span className="num font-semibold">{pct(o.prob, 1)}</span></div>
                  <div className="relative mt-1 h-2.5 rounded bg-ink-800" aria-hidden>
                    <div className="absolute h-full rounded bg-accent/25" style={{ left: `${o.lo * 100}%`, width: `${Math.max((o.hi - o.lo) * 100, 0.6)}%` }} />
                    <div className="absolute top-[-2px] h-[14px] w-0.5 bg-accent" style={{ left: `${o.prob * 100}%` }} />
                  </div>
                  <div className="num mt-0.5 text-[11px] text-fog-600">range {pct(o.lo, 1)} – {pct(o.hi, 1)}</div>
                </div>
              ))}
              <Disclaimer>{a.disclaimer}</Disclaimer>
            </div>
          )}
        </Panel>
        <div>{a ? <MomentumCard m={a.momentum} /> : <Loading />}</div>
      </div>
      <Panel title="Model explanation" subtitle="Why the model predicts this at the selected moment">
        {a?.explanation ? <ExplainPanel ex={a.explanation} outcomes={a.outcomes} onClass={setTargetClass} /> : a?.terminal ? <p className="text-sm text-fog-500">The match is decided - nothing left to explain.</p> : <Loading />}
      </Panel>
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <Panel title="Team analytics" subtitle="Live statistics at this moment">{t ? <CompareBars rows={t.rows} aName={t.a} bName={t.b} /> : <p className="text-sm text-fog-500">Team statistics for cricket are shown in the run-rate, partnership and wagon-wheel views of the Match Center.</p>}</Panel>
        <div className="space-y-3">
          <KeyPlayersCard players={a?.key_players} />
          <Link to={`/app/${sport}/players`} className="block rounded-md border hairline px-3 py-2 text-sm text-accent hover:bg-ink-800">Open Player Lab for predictions and comparisons</Link>
        </div>
      </div>
      <Panel title="Historical trends" subtitle="How the prediction and momentum evolved across this match">
        {series.data ? <div className="grid gap-4 lg:grid-cols-2"><WinProbChart series={series.data} step={step} onStep={setStep} labels={a?.outcomes.map((o) => o.label) ?? series.data.classes} height={200} /><MomentumChart series={series.data} step={step} onStep={setStep} height={200} /></div> : <Loading />}
      </Panel>
      {m && (
        <Panel title="About the model behind these numbers" actions={<Link to="/models" className="text-xs text-accent">Full evaluation</Link>}>
          <dl className="grid grid-cols-2 gap-x-6 sm:grid-cols-4"><Kv k="Algorithm" v={m.name} /><Kv k="Test accuracy" v={pct(m.accuracy, 1)} /><Kv k="ROC-AUC" v={m.roc_auc.toFixed(3)} /><Kv k="Brier score" v={m.brier.toFixed(3)} /></dl>
          <p className="mt-2 text-xs text-fog-500">Trained on {m.data_source}. Accuracy figures describe synthetic data and should not be read as real-world sports accuracy.</p>
        </Panel>
      )}
    </div>
  )
}
