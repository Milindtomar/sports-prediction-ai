export type Sport = 'cricket' | 'football' | 'basketball'
export const SPORTS: Sport[] = ['cricket', 'football', 'basketball']

export interface Outcome { label: string; prob: number; lo: number; hi: number; cls: number }
export interface MomentumFactor { label: string; points: number; detail: string; direction: 'positive' | 'negative' | 'neutral' }
export interface Momentum { score: number; label: string; tone: string; side: string; factors: MomentumFactor[]; formula: string }
export interface Contribution { feature: string; label: string; value: number; value_text: string; contribution_pp: number; direction: string; text: string; reference?: number }
export interface Explanation {
  target_class: number; target_label: string; probability: number; base_value: number
  simple: { headline: string; baseline_text: string; positives: { text: string; pp: number }[]; negatives: { text: string; pp: number }[] }
  technical: { method: string; model: string; additivity_gap_pp: number; global_importance: [string, number][]; table: Contribution[] }
  contributions: Contribution[]
}
export interface ModelCard { name: string; accuracy: number; f1: number; roc_auc: number; brier: number; log_loss: number; ece: number; calibrated: boolean; classes: string[]; dataset: any; data_source: string }
export interface TeamScore { name: string; score: string; sub: string; active: boolean }
export interface Scoreboard { teams: TeamScore[]; status: string; clock: string; venue: string; phase: string; innings?: number }
export interface Analysis {
  sport: Sport; state: Record<string, any>; scoreboard: Scoreboard; focus: { name: string; cls: number }
  outcomes: Outcome[]; headline: Outcome; terminal: boolean; momentum: Momentum; explanation: Explanation | null
  insights: string[]; features: Record<string, number>; model: ModelCard; disclaimer: string
  key_players?: KeyPlayer[]; step?: { i: number; n: number; label: string }
}
export interface KeyPlayer { name: string; team: string; role: string; headline: string; detail: string; value: number }
export interface MatchCard { id: number; sport: Sport; slug: string; title: string; home: string; away: string; venue: string; status: string; n_steps: number; result?: string }
export interface MatchDetail extends MatchCard { meta: Record<string, any>; timeline: Record<string, any>[]; events: Record<string, any>[] }
export interface SeriesStep { i: number; label: string; probs: number[]; lo: number[]; hi: number[]; terminal: boolean; momentum: number; clock: string; score: string[] }
export interface Series { match_id: number; sport: Sport; steps: SeriesStep[]; classes: string[]; focus_class: number }
export interface EventDef { id: string; label: string; group: string; description: string }
export interface ActionDef { id: string; label: string; description: string }
export interface SportMeta {
  key: Sport; name: string; tagline: string; classes: string[]; focus_class: number; analytics: string[]; coach_horizon: string
  events: EventDef[]; actions: ActionDef[]; features: Record<string, { label: string; good: number; unit: string }>
}
export interface SimResult {
  sport: Sport; applied: { id: string; label: string; count: number }[]
  before: Pick<Analysis, 'outcomes' | 'headline' | 'scoreboard' | 'momentum' | 'terminal' | 'state'>
  after: Pick<Analysis, 'outcomes' | 'headline' | 'scoreboard' | 'momentum' | 'terminal' | 'state'>
  deltas: { label: string; before: number; after: number; delta_pp: number }[]
  focus_class: number; narrative: string; pipeline: string[]
  attribution: null | { rows: { feature: string; label: string; before_text: string; after_text: string; contribution_pp: number }[]; total_pp: number; method: string }
}
export interface Sweep { baseline: number; focus_label: string; impacts: { id: string; label: string; group: string; prob: number; delta_pp: number }[] }
export interface CoachOption { id: string; label: string; description: string; value: number; se: number; p10: number; p90: number; stats: Record<string, number>; delta_vs_now: number; best: boolean }
export interface Coach {
  available: boolean; reason?: string; side?: string; situation?: string; recommendation?: string; recommendation_id?: string
  confidence?: number; metric?: string; current_value?: number; horizon?: string; n_rollouts?: number
  framing: string; options?: CoachOption[]; confidence_note?: string
  [k: string]: any
}
export interface PlayerRow { id: number; name: string; team: string; role: string; sport: Sport; attrs: Record<string, any> }
export interface PredVal { value: number; lo: number | null; hi: number | null }
export interface PlayerNext { player: PlayerRow; label: string; disclaimer: string; kinds: Record<string, { predictions: Record<string, PredVal>; performance_score: number; context: Record<string, any>; n_games: number }> }
export interface PlayerProfile { player: PlayerRow; kinds: Record<string, { metrics: { feature: string; label: string; value: number; peer_mean: number; z: number; percentile: number }[]; strengths: any[]; weaknesses: any[]; notes: string[]; method: string }> }
export interface PlayerHistory { kinds: Record<string, { game: number; predicted: Record<string, number>; actual: Record<string, number> }[]>; label_pred: string; label_actual: string }
export interface PlayerDetail { player: PlayerRow; next_game: PlayerNext; profile: PlayerProfile; history: PlayerHistory }
export interface HciTask { id: string; sport: Sport; kind: 'read' | 'why' | 'whatif'; title: string; prompt: string; state: Record<string, any>; options: { id: string; label: string }[] }
