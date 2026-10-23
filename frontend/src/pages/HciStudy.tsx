import { useEffect, useRef, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { PredictionInterface } from '../components/HciInterfaces'
import { Btn, EmptyState, ErrorState, Kv, Loading, Panel, Pill, Segmented } from '../components/ui'
import { api } from '../lib/api'
import { cn, errMsg, pct } from '../lib/format'
import { useAsync } from '../lib/hooks'
import type { HciTask } from '../lib/types'

type Tab = 'run' | 'compare' | 'results'
const LIKERT7 = [1, 2, 3, 4, 5, 6, 7]

export default function HciStudy() {
  const [tab, setTab] = useState<Tab>('run')
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="max-w-2xl">
          <h1 className="text-xl font-semibold tracking-tight">HCI study</h1>
          <p className="text-sm text-fog-500">Does an explainable, interactive interface improve understanding and decisions compared with a bare probability? Participants complete five tasks on one interface (A or B), then the System Usability Scale.</p>
        </div>
        <Segmented label="Study view" value={tab} onChange={setTab} options={[{ value: 'run', label: 'Run study' }, { value: 'compare', label: 'Side by side' }, { value: 'results', label: 'Results' }]} />
      </div>
      {tab === 'run' && <RunStudy onDone={() => setTab('results')} />}
      {tab === 'compare' && <SideBySide />}
      {tab === 'results' && <Results />}
    </div>
  )
}

function SideBySide() {
  const st = useAsync(() => api.defaultState('cricket'), [])
  if (st.error) return <ErrorState error={st.error} onRetry={st.reload} />
  if (!st.data) return <Loading />
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <Panel title="Interface A · simple prediction" subtitle="Probability only"><PredictionInterface variant="A" sport="cricket" state={st.data} /></Panel>
      <Panel title="Interface B · interactive explainable prediction" subtitle="Probability, reasons and a what-if panel"><PredictionInterface variant="B" sport="cricket" state={st.data} /></Panel>
    </div>
  )
}

function RunStudy({ onDone }: { onDone: () => void }) {
  const cfg = useAsync(() => api.hciTasks(), [])
  const [stage, setStage] = useState<'intro' | 'task' | 'sus' | 'done'>('intro')
  const [name, setName] = useState('')
  const [exp, setExp] = useState('Some experience')
  const [force, setForce] = useState<'auto' | 'A' | 'B'>('auto')
  const [agree, setAgree] = useState(false)
  const [session, setSession] = useState<{ id: number; condition: 'A' | 'B' } | null>(null)
  const [idx, setIdx] = useState(0)
  const [err, setErr] = useState<Error | null>(null)
  const [answers, setAnswers] = useState<Record<string, boolean>>({})
  const [susScore, setSusScore] = useState<number | null>(null)

  const start = async () => {
    setErr(null)
    try { setSession(await api.hciCreate(name.trim(), exp, agree, force === 'auto' ? undefined : force)); setIdx(0); setAnswers({}); setStage('task') }
    catch (e) { setErr(new Error(`Could not start the session: ${errMsg(e)}`)) }
  }
  if (cfg.error) return <ErrorState error={cfg.error} onRetry={cfg.reload} />
  if (!cfg.data) return <Loading />

  if (stage === 'intro')
    return (
      <Panel title="Start a session" subtitle="Each participant sees only one interface. Assignment alternates A, B, A, B… to keep groups balanced.">
        <form className="grid max-w-xl gap-3" onSubmit={(e) => { e.preventDefault(); if (name.trim() && agree) start() }}>
          <section aria-label="Consent" className="rounded-md border hairline p-3 text-sm text-fog-300">
            <h3 className="mb-1 font-medium text-fog-100">Before you start</h3>
            <p>{cfg.data.consent_text}</p>
            <label className="mt-3 flex items-start gap-2 text-fog-100"><input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} className="mt-1 accent-[rgb(var(--accent))]" /> I have read this and agree to take part. I know I can stop at any time.</label>
          </section>
          <label className="text-sm">Anonymous participant code<input value={name} onChange={(e) => setName(e.target.value)} maxLength={60} required pattern="[A-Za-z0-9 _.\-]+" title="Letters, numbers, spaces, dot, dash or underscore. Do not use your real name." className="mt-1 w-full rounded-md border hairline bg-ink-950 px-3 py-2" placeholder="e.g. P07 (not your real name)" /></label>
          <label className="text-sm">Sports analytics experience<select value={exp} onChange={(e) => setExp(e.target.value)} className="mt-1 w-full rounded-md border hairline bg-ink-950 px-3 py-2"><option>No experience</option><option>Some experience</option><option>Regular analytics user</option></select></label>
          <div className="text-sm">Interface assignment <Segmented label="Assignment" value={force} onChange={setForce} options={[{ value: 'auto', label: 'Auto (balanced)' }, { value: 'A', label: 'Force A' }, { value: 'B', label: 'Force B' }]} />
            <p className="mt-1 text-xs text-fog-500">Forcing a condition is for demonstrations; use Auto when collecting real data.</p></div>
          {err && <ErrorState error={err} />}
          <div><Btn type="submit" disabled={!name.trim() || !agree}>Begin tasks</Btn></div>
        </form>
        <p className="mt-4 text-xs text-fog-500">Collected: task time, decision accuracy (against model-derived ground truth), confidence, trust in AI, number of interactions and SUS score. No personal data beyond the anonymous code you enter is stored.</p>
      </Panel>
    )

  if (stage === 'task' && session) {
    // Latin-square style rotation: each session starts at a different task, which spreads order/learning effects across participants.
    const all = cfg.data.tasks, off = session.id % all.length
    const ordered = [...all.slice(off), ...all.slice(0, off)]
    const task = ordered[idx]
    return <TaskScreen key={task.id} task={task} n={idx + 1} total={ordered.length} session={session}
      onSubmitted={(ok) => { setAnswers((a) => ({ ...a, [task.id]: ok })); if (idx + 1 < ordered.length) setIdx(idx + 1); else setStage('sus') }} />
  }

  if (stage === 'sus' && session)
    return <SusForm items={cfg.data.sus_items} trustItems={cfg.data.trust_items} sessionId={session.id} onDone={(s) => { setSusScore(s); setStage('done') }} />

  const correct = Object.values(answers).filter(Boolean).length
  return (
    <Panel title="Session complete">
      <dl className="max-w-sm"><Kv k="Interface" v={session?.condition} /><Kv k="Correct decisions" v={`${correct} / ${Object.keys(answers).length}`} /><Kv k="SUS score" v={susScore?.toFixed(1)} /></dl>
      <div className="mt-3 flex gap-2"><Btn onClick={() => { setStage('intro'); setName('') }}>New participant</Btn><Btn variant="ghost" onClick={onDone}>View results</Btn></div>
    </Panel>
  )
}

function TaskScreen({ task, n, total, session, onSubmitted }: { task: HciTask; n: number; total: number; session: { id: number; condition: 'A' | 'B' }; onSubmitted: (ok: boolean) => void }) {
  const t0 = useRef(performance.now())
  const [inter, setInter] = useState(0)
  const [choice, setChoice] = useState('')
  const [conf, setConf] = useState(0)
  const [trust, setTrust] = useState(0)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<Error | null>(null)
  useEffect(() => { t0.current = performance.now() }, [])
  const submit = async () => {
    setBusy(true); setErr(null)
    try {
      const r = await api.hciResult(session.id, { task_id: task.id, position: n, answer: choice, time_ms: Math.round(performance.now() - t0.current), confidence: conf, trust, interactions: inter })
      onSubmitted(r.correct)
    } catch (e) { setErr(new Error(`Your answer was not saved: ${errMsg(e)}`)) } finally { setBusy(false) }
  }
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <Panel title={`Task ${n} of ${total} · ${task.title}`} subtitle={`Interface ${session.condition}`} actions={<Pill>{task.sport}</Pill>}>
        <PredictionInterface variant={session.condition} sport={task.sport} state={task.state} sessionId={session.id} onInteract={() => setInter((x) => x + 1)} />
      </Panel>
      <Panel title="Your answer">
        <fieldset><legend className="mb-2 text-sm font-medium">{task.prompt}</legend>
          <div className="space-y-1.5">{task.options.map((o) => (
            <label key={o.id} className={cn('flex cursor-pointer items-center gap-2 rounded-md border hairline px-3 py-2 text-sm', choice === o.id && 'border-accent bg-accent/5')}><input type="radio" name="answer" checked={choice === o.id} onChange={() => setChoice(o.id)} className="accent-[rgb(var(--accent))]" />{o.label}</label>))}</div></fieldset>
        <Likert label="How confident are you in this answer?" low="Not at all" high="Completely" value={conf} onChange={setConf} />
        <Likert label="How much do you trust the AI prediction shown?" low="Not at all" high="Completely" value={trust} onChange={setTrust} />
        {err && <div className="mt-3"><ErrorState error={err} onRetry={submit} /></div>}
        <div className="mt-4"><Btn onClick={submit} disabled={!choice || !conf || !trust || busy}>{busy ? 'Saving…' : n === total ? 'Submit and continue to questionnaire' : 'Submit answer'}</Btn></div>
      </Panel>
    </div>
  )
}

function Likert({ label, low, high, value, onChange }: { label: string; low: string; high: string; value: number; onChange: (v: number) => void }) {
  return (
    <fieldset className="mt-4"><legend className="text-sm">{label}</legend>
      <div className="mt-1 flex items-center gap-1" role="radiogroup" aria-label={label}>
        <span className="mr-1 text-[11px] text-fog-500">{low}</span>
        {LIKERT7.map((v) => <button key={v} type="button" role="radio" aria-checked={value === v} onClick={() => onChange(v)} className={cn('num h-8 w-8 rounded-md border hairline text-sm', value === v ? 'border-accent bg-accent text-ink-950' : 'hover:bg-ink-800')}>{v}</button>)}
        <span className="ml-1 text-[11px] text-fog-500">{high}</span>
      </div></fieldset>
  )
}

function SusForm({ items, trustItems, sessionId, onDone }: { items: string[]; trustItems: string[]; sessionId: number; onDone: (s: number) => void }) {
  const [vals, setVals] = useState<number[]>(Array(10).fill(0))
  const [trust, setTrust] = useState<number[]>(Array(trustItems.length).fill(0))
  const [feedback, setFeedback] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<Error | null>(null)
  const submit = async () => {
    setBusy(true); setErr(null)
    try { onDone((await api.hciSus(sessionId, vals, trust, feedback.trim())).sus_score) } catch (e) { setErr(new Error(`Questionnaire not saved: ${errMsg(e)}`)) } finally { setBusy(false) }
  }
  return (
    <div className="space-y-3">
      <Panel title="System Usability Scale" subtitle="1 = strongly disagree, 5 = strongly agree">
        <ol className="space-y-3">{items.map((it, i) => (
          <li key={i}><p className="text-sm">{i + 1}. {it}</p>
            <div className="mt-1 flex gap-1" role="radiogroup" aria-label={`SUS item ${i + 1}`}>{[1, 2, 3, 4, 5].map((v) => <button key={v} type="button" role="radio" aria-checked={vals[i] === v} onClick={() => setVals(vals.map((x, j) => (j === i ? v : x)))} className={cn('num h-8 w-10 rounded-md border hairline text-sm', vals[i] === v ? 'border-accent bg-accent text-ink-950' : 'hover:bg-ink-800')}>{v}</button>)}</div></li>))}</ol>
      </Panel>
      <Panel title="Trust in the AI prediction" subtitle="1 = strongly disagree, 7 = strongly agree. These four items were written for this study; they are not a validated scale.">
        <ol className="space-y-3">{trustItems.map((it, i) => (
          <li key={i}><p className="text-sm">{i + 1}. {it}</p>
            <div className="mt-1 flex gap-1" role="radiogroup" aria-label={`Trust item ${i + 1}`}>{[1, 2, 3, 4, 5, 6, 7].map((v) => <button key={v} type="button" role="radio" aria-checked={trust[i] === v} onClick={() => setTrust(trust.map((x, j) => (j === i ? v : x)))} className={cn('num h-8 w-8 rounded-md border hairline text-sm', trust[i] === v ? 'border-accent bg-accent text-ink-950' : 'hover:bg-ink-800')}>{v}</button>)}</div></li>))}</ol>
        <label className="mt-4 block text-sm">Anything else you want to tell us? (optional, please do not include personal details)
          <textarea value={feedback} onChange={(e) => setFeedback(e.target.value)} maxLength={500} rows={3} className="mt-1 w-full rounded-md border hairline bg-ink-950 px-3 py-2" />
          <span className="text-xs text-fog-500">{feedback.length}/500</span></label>
        {err && <div className="mt-3"><ErrorState error={err} onRetry={submit} /></div>}
        <div className="mt-4"><Btn onClick={submit} disabled={busy || vals.some((v) => !v) || trust.some((v) => !v)}>{busy ? 'Saving…' : 'Finish'}</Btn></div>
      </Panel>
    </div>
  )
}

function Results() {
  const r = useAsync(() => api.hciResults(), [])
  if (r.error) return <ErrorState error={r.error} onRetry={r.reload} />
  if (!r.data) return <Loading />
  const d = r.data, A = d.groups.A, B = d.groups.B
  if (d.n_sessions === 0 || (A.tasks + B.tasks) === 0)
    return <Panel title="Results"><EmptyState title="No participant data yet" hint="Run the study with at least one participant per interface. Results appear here and are never pre-filled." /></Panel>
  const f = (v: number | null | undefined, dp = 1) => (v == null ? '–' : v.toFixed(dp))
  const rows: [string, any, any, any][] = [
    ['Participants', A.participants, B.participants, null],
    ['Task time (s)', f(A.time_s.mean), f(B.time_s.mean), d.tests.time],
    ['Decision accuracy', A.accuracy == null ? '–' : pct(A.accuracy), B.accuracy == null ? '–' : pct(B.accuracy), d.tests.accuracy],
    ['Confidence (1–7)', f(A.confidence.mean, 2), f(B.confidence.mean, 2), d.tests.confidence],
    ['Trust in AI, single rating (1–7)', f(A.trust.mean, 2), f(B.trust.mean, 2), d.tests.trust],
    ['Trust items, mean of 4 (1–7, study-specific)', f(A.trust_scale?.mean, 2), f(B.trust_scale?.mean, 2), d.tests.trust_scale],
    ['Interactions per task', f(A.interactions.mean, 1), f(B.interactions.mean, 1), null],
    ['SUS (0–100)', f(A.sus.mean), f(B.sus.mean), d.tests.sus],
  ]
  const chart = d.per_task.map((t: any) => ({ task: t.id, A: t.A.accuracy == null ? 0 : +(t.A.accuracy * 100).toFixed(0), B: t.B.accuracy == null ? 0 : +(t.B.accuracy * 100).toFixed(0) }))
  return (
    <div className="space-y-3">
      <Panel title="Interface A vs Interface B" actions={<span className="flex gap-3 text-xs"><a className="text-accent" href={api.hciExportUrl()} download>Download CSV</a><a className="text-accent" href={api.hciExportJsonUrl()} download>Download JSON</a></span>}>
        <table className="w-full text-sm"><thead className="text-left text-xs text-fog-500"><tr><th className="py-1 font-medium">Measure</th><th className="font-medium">A · simple</th><th className="font-medium">B · explainable</th><th className="text-right font-medium">Test (B vs A)</th></tr></thead>
          <tbody className="divide-y divide-ink-700">{rows.map(([k, a, b, t]) => <tr key={k}><td className="py-2">{k}</td><td className="num">{a}</td><td className="num">{b}</td><td className="num text-right text-xs text-fog-500">{t ? `p = ${t.p.toFixed(3)}${t.cohen_d != null ? `, d = ${t.cohen_d.toFixed(2)}` : ''}` : '–'}</td></tr>)}</tbody></table>
        <p className="mt-2 text-xs text-fog-500">{d.note}</p>
      </Panel>
      <Panel title="Accuracy by task (%)"><div role="img" aria-label="Accuracy by task and interface"><ResponsiveContainer width="100%" height={220}><BarChart data={chart} margin={{ left: -14 }}><CartesianGrid stroke="#243040" strokeDasharray="2 4" vertical={false} /><XAxis dataKey="task" stroke="#334357" /><YAxis domain={[0, 100]} stroke="#334357" /><Legend wrapperStyle={{ fontSize: 12 }} /><Tooltip cursor={{ fill: '#18222B' }} contentStyle={{ background: '#121A21', border: '1px solid #243040', borderRadius: 8, fontSize: 12 }} /><Bar dataKey="A" name="A · simple" fill="#66737F" isAnimationActive={false} /><Bar dataKey="B" name="B · explainable" fill="rgb(var(--accent))" isAnimationActive={false} /></BarChart></ResponsiveContainer></div></Panel>
    </div>
  )
}
