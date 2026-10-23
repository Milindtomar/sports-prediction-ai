import { Panel } from '../components/ui'
import { CompareBars, CmpRow } from '../components/charts/CompareBars'
import { PartnershipPanel, PitchMap, RunRateChart, ScoreProgression, WagonWheel } from '../components/charts/CricketViz'
import { ShotMap, XgTimeline } from '../components/charts/FootballViz'
import { CourtShotChart, ScoreProgressionBB } from '../components/charts/BasketballViz'
import type { MatchDetail, Sport } from '../lib/types'

const f1 = (v: number) => v.toFixed(1)
const pc = (v: number) => `${(v * 100).toFixed(0)}%`

export function teamRows(sport: Sport, s: Record<string, any>): { rows: CmpRow[]; a: string; b: string } | null {
  if (sport === 'football')
    return { a: s.home_team, b: s.away_team, rows: [
      { label: 'Possession %', a: s.home_possession, b: 100 - s.home_possession, fmt: (v) => v.toFixed(0) },
      { label: 'Shots', a: s.home_shots, b: s.away_shots }, { label: 'Shots on target', a: s.home_sot, b: s.away_sot },
      { label: 'Expected goals (xG)', a: s.home_xg, b: s.away_xg, fmt: (v) => v.toFixed(2) }, { label: 'Corners', a: s.home_corners, b: s.away_corners },
      { label: 'Pass accuracy %', a: s.home_pass_acc, b: s.away_pass_acc, fmt: f1 }, { label: 'Fouls', a: s.home_fouls, b: s.away_fouls, lowerBetter: true },
      { label: 'Yellow cards', a: s.home_yellow, b: s.away_yellow, lowerBetter: true }, { label: 'Red cards', a: s.home_red, b: s.away_red, lowerBetter: true },
    ] }
  if (sport === 'basketball') {
    const poss = (p: 'home' | 'away') => s[`${p}_fga`] + 0.44 * s[`${p}_fta`] + s[`${p}_tov`]
    const ppp = (p: 'home' | 'away') => (poss(p) > 0 ? s[`${p}_score`] / poss(p) : 0)
    const pctOf = (m: number, a: number) => (a ? m / a : 0)
    return { a: s.home_team, b: s.away_team, rows: [
      { label: 'Field-goal %', a: pctOf(s.home_fgm, s.home_fga), b: pctOf(s.away_fgm, s.away_fga), fmt: pc },
      { label: 'Three-point %', a: pctOf(s.home_3pm, s.home_3pa), b: pctOf(s.away_3pm, s.away_3pa), fmt: pc },
      { label: 'Free-throw %', a: pctOf(s.home_ftm, s.home_fta), b: pctOf(s.away_ftm, s.away_fta), fmt: pc },
      { label: 'Points per possession', a: ppp('home'), b: ppp('away'), fmt: (v) => v.toFixed(2) },
      { label: 'Rebounds', a: s.home_reb, b: s.away_reb }, { label: 'Assists', a: s.home_ast, b: s.away_ast },
      { label: 'Turnovers', a: s.home_tov, b: s.away_tov, lowerBetter: true }, { label: 'Fouls', a: s.home_fouls, b: s.away_fouls, lowerBetter: true },
    ] }
  }
  return null
}

/** Sport-specific visualisation set. The core pages stay generic; only this component knows about the sport. */
export function SportPanels({ sport, detail, step }: { sport: Sport; detail: MatchDetail; step: number }) {
  const tl = detail.timeline, ev = detail.events, st = tl[step]
  if (sport === 'cricket')
    return (
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
        <Panel title="Run rate" subtitle="Current vs required rate, runs per over"><RunRateChart timeline={tl} step={step} /></Panel>
        <Panel title="Score progression" subtitle="Both innings by over"><ScoreProgression timeline={tl} step={step} /></Panel>
        <Panel title="Wagon wheel" subtitle="Scoring shots this innings (illustrative placement)"><WagonWheel events={ev} st={st} /></Panel>
        <Panel title="Bowling & pitch map" subtitle="Length and line of recent deliveries"><PitchMap events={ev} st={st} /></Panel>
        <Panel title="Partnership analysis" subtitle="Runs (balls) between wickets" className="xl:col-span-2"><PartnershipPanel events={ev} st={st} /></Panel>
      </div>
    )
  const t = teamRows(sport, st)!
  if (sport === 'football')
    return (
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
        <Panel title="Shot map" subtitle="All shots so far, sized by xG"><ShotMap events={ev} st={st} home={st.home_team} away={st.away_team} /></Panel>
        <Panel title="xG timeline" subtitle="Cumulative expected goals"><XgTimeline timeline={tl} step={step} events={ev} /></Panel>
        <Panel title="Team comparison" subtitle="Live match statistics" className="xl:col-span-2"><CompareBars rows={t.rows} aName={t.a} bName={t.b} /></Panel>
      </div>
    )
  return (
    <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
      <Panel title="Score progression" subtitle="Points by game minute with margin"><ScoreProgressionBB timeline={tl} step={step} /></Panel>
      <Panel title="Shot chart" subtitle="Made and missed shots"><CourtShotChart events={ev} st={st} home={st.home_team} away={st.away_team} /></Panel>
      <Panel title="Team efficiency" subtitle="Shooting, possession efficiency and control" className="xl:col-span-2"><CompareBars rows={t.rows} aName={t.a} bName={t.b} /></Panel>
    </div>
  )
}
