import { Pause, Play, SkipBack, SkipForward } from 'lucide-react'
import { useMatch } from '../../lib/MatchContext'
import { Btn, Loading, LiveDot } from '../ui'

export function TimelineControls() {
  const { match, step, setStep, playing, setPlaying, matches, matchId, selectMatch } = useMatch()
  const tl = match.data?.timeline
  return (
    <div className="rounded-lg border hairline bg-ink-900 p-3">
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex min-w-0 items-center gap-2 text-xs text-fog-500">
          <span>Match</span>
          <select aria-label="Select match" value={matchId ?? ''} onChange={(e) => selectMatch(+e.target.value)}
            className="max-w-[260px] truncate rounded-md border hairline bg-ink-950 px-2 py-1.5 text-sm text-fog-100">
            {matches.data?.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}
          </select>
        </label>
        <LiveDot />
        <div className="ml-auto flex items-center gap-1">
          <Btn variant="quiet" aria-label="Previous step" onClick={() => setStep(step - 1)} disabled={!tl || step <= 0}><SkipBack className="h-4 w-4" /></Btn>
          <Btn variant="ghost" aria-label={playing ? 'Pause replay' : 'Play replay'} onClick={() => setPlaying(!playing)} disabled={!tl}>{playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}{playing ? 'Pause' : 'Replay'}</Btn>
          <Btn variant="quiet" aria-label="Next step" onClick={() => setStep(step + 1)} disabled={!tl || step >= (tl?.length ?? 1) - 1}><SkipForward className="h-4 w-4" /></Btn>
        </div>
      </div>
      {!tl ? <Loading label="Loading match" height="h-10" /> : (
        <div className="mt-2 flex items-center gap-3">
          <input type="range" min={0} max={tl.length - 1} value={step} onChange={(e) => { setPlaying(false); setStep(+e.target.value) }} aria-label="Match timeline" className="h-1.5 w-full cursor-pointer accent-[rgb(var(--accent))]" />
          <span className="num w-28 shrink-0 text-right text-xs text-fog-300">{tl[step]?.step_label}</span>
        </div>
      )}
    </div>
  )
}
