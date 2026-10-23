import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts'
import { useState } from 'react'
import { ErrorState, Kv, Loading, Panel, Pill, Segmented } from '../components/ui'
import { api } from '../lib/api'
import { cn, pct, sportLabel } from '../lib/format'
import { useAsync } from '../lib/hooks'
import { useMatch } from '../lib/MatchContext'
import { SPORTS, Sport } from '../lib/types'

const ALGO = ['logistic_regression', 'random_forest', 'gradient_boosting', 'xgboost']
const NAME: Record<string, string> = { logistic_regression: 'Logistic Regression', random_forest: 'Random Forest', gradient_boosting: 'Gradient Boosting (Hist)', xgboost: 'XGBoost' }
const PLAYER_TASK: Record<Sport, string[]> = {
  cricket: ['cricket_runs', 'cricket_p50', 'cricket_wickets', 'cricket_economy'], football: ['football_goals', 'football_assists', 'football_shots'], basketball: ['basketball_points', 'basketball_rebounds', 'basketball_assists'],
}
const tip = { background: '#121A21', border: '1px solid #243040', borderRadius: 8, fontSize: 12 }

export default function ModelInsights() {
  const ctx = useSafeSport()
  const [sport, setSport] = useState<Sport>(ctx)
  const m = useAsync(() => api.models(), [])
  const meta = useAsync(() => api.meta(sport), [sport])
  if (m.error) return <ErrorState error={m.error} onRetry={m.reload} title="Model metrics unavailable" />
  if (!m.data) return <Loading label="Loading evaluation" height="h-60" />
  const r = m.data.sports[sport]
  const t = r.final.test
  const rel = (t.reliability as any[]).map((b) => ({ x: +(b.mean_pred * 100).toFixed(1), y: +(b.frac_pos * 100).toFixed(1), n: b.n }))
  const imp = Object.entries(r.feature_importance as Record<string, number>).slice(0, 10).map(([k, v]) => ({ name: meta.data?.features[k]?.label ?? k, v: +v.toFixed(4) }))
  const multi = r.classes.length === 3
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h1 className="text-xl font-semibold tracking-tight">Model insights</h1><p className="text-sm text-fog-500">Datasets, algorithms and evaluation, reported on a held-out chronological test set.</p></div>
        <Segmented label="Sport" value={sport} onChange={setSport} options={SPORTS.map((s) => ({ value: s, label: sportLabel[s] }))} />
      </div>
      <div className="rounded-md border border-warn/40 bg-warn/5 p-3 text-sm text-warn">All figures describe <b>synthetic data</b> from reproducible simulators ({m.data.meta.data_source}). They validate the pipeline, not real-world sports accuracy.</div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <Panel title="Dataset" className="lg:col-span-1">
          <dl>
            <Kv k="Source" v="Synthetic simulator" /><Kv k="Generator" v={r.dataset.generator} /><Kv k="Snapshots" v={r.dataset.rows.toLocaleString()} /><Kv k="Matches" v={r.dataset.matches.toLocaleString()} />
            <Kv k="Features" v={r.dataset.n_features} /><Kv k="Target" v={r.dataset.target} /><Kv k="Snapshot rule" v={r.dataset.snapshot} />
            <Kv k="Split" v={r.split.scheme} /><Kv k="Train / val / test matches" v={`${r.split.matches.train} / ${r.split.matches.validation} / ${r.split.matches.test}`} />
            <Kv k="Data hash" v={r.dataset.data_hash} /><Kv k="Dataset version" v={m.data.meta.dataset_version ?? 'not available (retrain to record)'} /><Kv k="Model version" v={m.data.meta.model_version ?? 'not available (retrain to record)'} /><Kv k="Random seed" v={m.data.meta.seeds?.[sport] ?? 'not available'} />
          </dl>
          <p className="mt-2 text-xs text-fog-500">Class balance: {Object.entries(r.dataset.class_balance).map(([k, v]) => `${r.classes[+k]} ${pct(v as number)}`).join(' · ')}</p>
          <p className="mt-2 text-xs text-fog-500">Leakage control: features use only information available at the snapshot (no final score, result or future events); pre-match team ratings are Elo values updated only <i>after</i> each match.</p>
        </Panel>
        <Panel title="Features" className="lg:col-span-2" subtitle="Direction: + higher helps the headline side, − higher hurts, blank = context">
          {!meta.data ? <Loading height="h-24" /> : (
            <ul className="grid gap-x-6 gap-y-1 sm:grid-cols-2">{(r.features as string[]).map((f) => <li key={f} className="flex justify-between border-b border-ink-800 py-1 text-sm"><span>{meta.data!.features[f]?.label ?? f}</span><span className="num text-fog-600">{f} {meta.data!.features[f]?.good ? (meta.data!.features[f].good > 0 ? '+' : '−') : ''}</span></li>)}</ul>
          )}
        </Panel>
      </div>

      <Panel title="Algorithm comparison" subtitle={`Selection rule: ${r.selection_rule}. We do not pick the most complex model by default.`}>
        <div className="overflow-x-auto scroll-thin">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="text-left text-xs text-fog-500"><tr><th className="py-1.5 font-medium">Algorithm</th><th className="font-medium">Val log-loss</th><th className="font-medium">Test accuracy</th><th className="font-medium">Precision</th><th className="font-medium">Recall</th><th className="font-medium">F1</th><th className="font-medium">ROC-AUC</th><th className="font-medium">Brier</th><th className="font-medium">Train s</th></tr></thead>
            <tbody className="divide-y divide-ink-700">
              {ALGO.map((a) => { const c = r.comparison[a]; const x = c.test; return (
                <tr key={a} className={cn(r.chosen === a && 'bg-accent/5')}><td className="py-2">{NAME[a]} {r.chosen === a && <Pill tone="live">selected</Pill>}</td><td className="num">{c.validation.log_loss.toFixed(4)}</td><td className="num">{pct(x.accuracy, 1)}</td><td className="num">{x.precision.toFixed(3)}</td><td className="num">{x.recall.toFixed(3)}</td><td className="num">{x.f1.toFixed(3)}</td><td className="num">{x.roc_auc.toFixed(3)}</td><td className="num">{x.brier.toFixed(3)}</td><td className="num text-fog-500">{c.train_seconds}</td></tr>) })}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-fog-500">{multi ? 'Precision, recall and F1 are macro-averaged over home/draw/away; ROC-AUC is one-vs-rest macro; Brier is the multi-class sum of squared errors.' : ''} Baselines: always predicting the majority class gives {pct(r.baseline.majority_accuracy, 1)} accuracy and log-loss {r.baseline.prior_log_loss.toFixed(3)}; the selected model scores {pct(t.accuracy, 1)} and {t.log_loss.toFixed(3)}. Differences between the four algorithms are small because the generating process is close to log-linear in the engineered features.</p>
      </Panel>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <Panel title={`Selected model: ${r.chosen_display}`} subtitle="Held-out test set">
          <dl><Kv k="Accuracy" v={pct(t.accuracy, 1)} /><Kv k="Precision" v={t.precision.toFixed(3)} /><Kv k="Recall" v={t.recall.toFixed(3)} /><Kv k="F1 score" v={t.f1.toFixed(3)} /><Kv k="ROC-AUC" v={t.roc_auc.toFixed(3)} /><Kv k="Brier score" v={t.brier.toFixed(4)} /><Kv k="Log-loss" v={t.log_loss.toFixed(4)} /><Kv k="Expected calibration error" v={t.ece.toFixed(4)} /><Kv k="Isotonic calibration" v={r.calibrated ? 'applied' : 'not needed (hurt validation)'} /><Kv k="Bootstrap members" v={r.bootstrap_members} /></dl>
        </Panel>
        <Panel title="Calibration" subtitle={multi ? 'Top-label confidence vs observed accuracy' : 'Predicted vs observed win frequency'}>
          <div role="img" aria-label="Reliability diagram"><div aria-hidden="true"><ResponsiveContainer width="100%" height={230}>
            <ScatterChart margin={{ top: 8, right: 12, left: -10, bottom: 8 }}>
              <CartesianGrid stroke="#243040" strokeDasharray="2 4" /><XAxis type="number" dataKey="x" domain={[0, 100]} name="Predicted" unit="%" stroke="#334357" /><YAxis type="number" dataKey="y" domain={[0, 100]} name="Observed" unit="%" stroke="#334357" /><ZAxis dataKey="n" range={[30, 160]} />
              <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 100, y: 100 }]} stroke="#66737F" strokeDasharray="4 3" />
              <Tooltip contentStyle={tip} cursor={{ strokeDasharray: '3 3' }} /><Scatter data={rel} fill="rgb(var(--accent))" line={{ stroke: 'rgb(var(--accent))' }} isAnimationActive={false} />
            </ScatterChart></ResponsiveContainer></div></div>
        </Panel>
        <Panel title="Feature importance" subtitle="Permutation importance: log-loss increase when a feature is shuffled">
          <div role="img" aria-label="Feature importance"><ResponsiveContainer width="100%" height={250}>
            <BarChart data={imp} layout="vertical" margin={{ left: 0, right: 12, top: 4, bottom: 0 }}><XAxis type="number" stroke="#334357" /><YAxis type="category" dataKey="name" width={140} stroke="#334357" tick={{ fontSize: 10 }} /><Tooltip contentStyle={tip} cursor={{ fill: '#18222B' }} /><Bar dataKey="v" fill="rgb(var(--accent))" radius={2} isAnimationActive={false} /></BarChart>
          </ResponsiveContainer></div>
        </Panel>
      </div>

      <Panel title="Confusion matrix" subtitle="Held-out test set. Rows are the actual outcome, columns the predicted one (most likely class).">
        {Array.isArray(t.confusion_matrix) ? (
          <div className="overflow-x-auto scroll-thin">
            <table className="text-sm">
              <caption className="sr-only">Confusion matrix for {sportLabel[sport]}</caption>
              <thead><tr><th className="p-2 text-left text-xs font-medium text-fog-500">Actual \ Predicted</th>{(r.classes as string[]).map((c) => <th key={c} scope="col" className="p-2 text-xs font-medium text-fog-500">{c}</th>)}</tr></thead>
              <tbody>{t.confusion_matrix.map((row: number[], i: number) => {
                const tot = row.reduce((x, y) => x + y, 0) || 1
                return <tr key={i}><th scope="row" className="p-2 text-left text-xs font-medium text-fog-300">{r.classes[i]}</th>{row.map((v, j) => <td key={j} className={cn('num border hairline p-2 text-center', i === j && 'bg-accent/10 font-medium')}>{v.toLocaleString()}<div className="text-[11px] font-normal text-fog-500">{pct(v / tot)} of row</div></td>)}</tr>
              })}</tbody>
            </table>
          </div>
        ) : <p className="text-sm text-fog-500">Not available: these metrics were produced before confusion matrices were recorded. Re-run <code>python -m app.ml.train_all</code>.</p>}
      </Panel>

      <Panel title="Player performance models" subtitle="Regression metrics on a chronological test split (later games only)">
        <div className="overflow-x-auto scroll-thin"><table className="w-full min-w-[640px] text-sm">
          <thead className="text-left text-xs text-fog-500"><tr><th className="py-1.5 font-medium">Target</th><th className="font-medium">Selected</th><th className="font-medium">MAE</th><th className="font-medium">RMSE</th><th className="font-medium">R²</th><th className="font-medium">Mean-predictor MAE</th><th className="font-medium">Skill vs mean</th></tr></thead>
          <tbody className="divide-y divide-ink-700">{PLAYER_TASK[sport].map((k) => { const p = m.data!.players[k]; if (!p) return null
            if (p.task.startsWith('binary')) return <tr key={k}><td className="py-2">{k.replace(/^[a-z]+_/, '')} (50+ runs, classifier)</td><td>{p.chosen_display}</td><td colSpan={2} className="num text-fog-500">AUC {p.final.test.roc_auc.toFixed(3)} · Brier {p.final.test.brier.toFixed(3)}</td><td className="num">–</td><td className="num text-fog-500">–</td><td className="num text-fog-500">acc {pct(p.final.test.accuracy, 1)} vs {pct(p.baseline.majority_accuracy, 1)}</td></tr>
            const f = p.final.test, b = p.baseline_mean_predictor; const skill = 1 - f.rmse / b.rmse
            return <tr key={k}><td className="py-2">{k.replace(/^[a-z]+_/, '')}</td><td>{p.chosen_display}</td><td className="num">{f.mae.toFixed(3)}</td><td className="num">{f.rmse.toFixed(3)}</td><td className="num">{f.r2.toFixed(3)}</td><td className="num text-fog-500">{b.mae.toFixed(3)}</td><td className={cn('num', skill > 0.02 ? 'text-up' : 'text-warn')}>{skill > 0 ? '+' : ''}{(skill * 100).toFixed(1)}% RMSE</td></tr> })}</tbody>
        </table></div>
        <p className="mt-2 text-xs text-fog-500">Count outcomes (wickets, assists) are mostly noise per game, so R² is near zero even for a correct model; we report that honestly rather than hide it. “Likely range” in Player Lab uses the 10th–90th percentile of these test errors.</p>
      </Panel>

      <Panel title="Limitations">
        <ul className="list-disc space-y-1 pl-5 text-sm text-fog-300">
          <li>Data is simulated; real-world accuracy will differ and must be re-measured on public datasets (see ML documentation).</li>
          <li>Because the simulator is close to log-linear, regularised linear models perform as well as tree ensembles. This may not hold on real data.</li>
          <li>Explanations describe the model, not causal truth. Correlated features share credit.</li>
          <li>Wagon-wheel, pitch-map and shot-location graphics are illustrative, not model outputs.</li>
        </ul>
      </Panel>
    </div>
  )
}

function useSafeSport(): Sport {
  try { const s = localStorage.getItem('sportsai.sport'); return (s as Sport) || 'cricket' } catch { return 'cricket' }
}
