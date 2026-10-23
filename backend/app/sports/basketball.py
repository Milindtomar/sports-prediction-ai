"""Basketball adapter. Headline = P(home team wins). Momentum is expressed for the home side."""
from __future__ import annotations

import copy

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.sports.base import ActionDef, EventDef, FeatureMeta, MomentumPart, SportAdapter, momentum_from_parts
from app.sports.features import GAME_SEC, basketball_features
from app.synth import basketball as sim


class BasketballState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    home_team: str = Field("Harbor Hornets", max_length=40)
    away_team: str = Field("Summit Stags", max_length=40)
    elapsed_sec: int = Field(0, ge=0, le=GAME_SEC)
    home_score: int = Field(0, ge=0, le=200)
    away_score: int = Field(0, ge=0, le=200)
    possession: int = Field(0, ge=0, le=1)
    home_fgm: int = Field(0, ge=0, le=90)
    home_fga: int = Field(0, ge=0, le=150)
    away_fgm: int = Field(0, ge=0, le=90)
    away_fga: int = Field(0, ge=0, le=150)
    home_3pm: int = Field(0, ge=0, le=40)
    home_3pa: int = Field(0, ge=0, le=80)
    away_3pm: int = Field(0, ge=0, le=40)
    away_3pa: int = Field(0, ge=0, le=80)
    home_ftm: int = Field(0, ge=0, le=60)
    home_fta: int = Field(0, ge=0, le=80)
    away_ftm: int = Field(0, ge=0, le=60)
    away_fta: int = Field(0, ge=0, le=80)
    home_reb: int = Field(0, ge=0, le=90)
    away_reb: int = Field(0, ge=0, le=90)
    home_ast: int = Field(0, ge=0, le=60)
    away_ast: int = Field(0, ge=0, le=60)
    home_tov: int = Field(0, ge=0, le=40)
    away_tov: int = Field(0, ge=0, le=40)
    home_fouls: int = Field(0, ge=0, le=40)
    away_fouls: int = Field(0, ge=0, le=40)
    home_elo: float = Field(1500.0, ge=1000, le=2000)
    away_elo: float = Field(1500.0, ge=1000, le=2000)
    home_lineup: float = Field(0.0, ge=-1.0, le=0.0)
    away_lineup: float = Field(0.0, ge=-1.0, le=0.0)
    recent_points_home: int = Field(0, ge=0, le=60)
    recent_points_away: int = Field(0, ge=0, le=60)
    current_run: int = Field(0, ge=-40, le=40)

    @model_validator(mode="after")
    def _consistent(self):
        for side in ("home", "away"):
            g = lambda k: getattr(self, f"{side}_{k}")
            if g("fgm") > g("fga") or g("3pm") > g("3pa") or g("ftm") > g("fta"):
                raise ValueError(f"{side}: made shots cannot exceed attempts")
            if g("3pa") > g("fga") or g("3pm") > g("fgm"):
                raise ValueError(f"{side}: three-point numbers cannot exceed field-goal numbers")
        return self


def clock(sec: int) -> tuple[int, str]:
    q = min(4, sec // 720 + 1)
    left = (q * 720 - sec) if sec < GAME_SEC else 0
    return q, f"{left // 60}:{left % 60:02d}"


class BasketballAdapter(SportAdapter):
    key = "basketball"
    name = "Basketball"
    tagline = "Possession efficiency, runs & shot charts"
    classes = ["Away win", "Home win"]
    focus_class = 1
    state_model = BasketballState
    analytics = ["Win probability", "Momentum", "Score progression", "Shot chart", "Team efficiency",
                 "Player comparison", "What-if simulation", "AI Coach"]
    coach_horizon = "next 5 minutes of game time"
    feature_meta = {
        "time_remaining": FeatureMeta("Seconds remaining", 0, "{:.0f}", "s"), "quarter": FeatureMeta("Quarter", 0, "{:.0f}"),
        "score_diff": FeatureMeta("Score margin", 1, "{:+.0f}"), "lead_security": FeatureMeta("Lead vs time left", 1, "{:+.2f}"),
        "fg_pct_diff": FeatureMeta("FG% difference", 1, "{:+.3f}"), "tp_pct_diff": FeatureMeta("3P% difference", 1, "{:+.3f}"),
        "ft_pct_diff": FeatureMeta("FT% difference", 1, "{:+.3f}"), "reb_diff": FeatureMeta("Rebound difference", 1, "{:+.0f}"),
        "ast_diff": FeatureMeta("Assist difference", 1, "{:+.0f}"), "tov_diff": FeatureMeta("Turnover difference", -1, "{:+.0f}"),
        "foul_diff": FeatureMeta("Foul difference", -1, "{:+.0f}"), "possession": FeatureMeta("Ball possession", 1, "{:+.0f}"),
        "eff_diff": FeatureMeta("Points-per-possession edge", 1, "{:+.3f}"), "elo_diff": FeatureMeta("Pre-game rating gap", 1, "{:+.2f}"),
        "lineup_diff": FeatureMeta("Lineup strength gap", 1, "{:+.2f}"),
    }
    phrases = {
        "score_diff": ("Leading on the scoreboard ({score_diff:+.0f})", "Trailing on the scoreboard ({score_diff:+.0f})"),
        "lead_security": ("The margin is large for the time left", "The margin is small or negative for the time left"),
        "time_remaining": ("Time left helps the home side", "Clock is running against the home side"),
        "fg_pct_diff": ("Shooting better from the field", "Shooting worse from the field"),
        "tp_pct_diff": ("Hot from three-point range", "Cold from three-point range"),
        "ft_pct_diff": ("Better at the free-throw line", "Worse at the free-throw line"),
        "reb_diff": ("Winning the rebound battle ({reb_diff:+.0f})", "Losing the rebound battle ({reb_diff:+.0f})"),
        "ast_diff": ("More ball movement (assists {ast_diff:+.0f})", "Less ball movement (assists {ast_diff:+.0f})"),
        "tov_diff": ("Taking care of the ball", "Turning the ball over more"),
        "foul_diff": ("Cleaner defensively on fouls", "Foul trouble is building"),
        "eff_diff": ("More efficient with each possession", "Less efficient with each possession"),
        "elo_diff": ("Stronger team on pre-game rating", "Weaker team on pre-game rating"),
        "lineup_diff": ("Full-strength lineup", "A key player is out of the lineup"),
        "possession": ("Has the ball now", "Opponent has the ball now"),
        "quarter": ("Quarter stage favours home", "Quarter stage favours the visitors"),
    }
    events = [
        EventDef("home_three", "Home hits a 3-pointer", "Scoring", "+3 home, 15s"),
        EventDef("away_three", "Opponent hits a 3-pointer", "Scoring", "+3 away, 15s"),
        EventDef("home_two", "Home scores inside", "Scoring", "+2 home, 15s"),
        EventDef("away_two", "Opponent scores inside", "Scoring", "+2 away, 15s"),
        EventDef("home_turnover", "Home turnover", "Possession", "Possession flips"),
        EventDef("away_turnover", "Opponent turnover", "Possession", "Possession flips"),
        EventDef("home_run", "Home 8–0 run", "Runs", "+8 home unanswered"),
        EventDef("away_run", "Opponent 8–0 run", "Runs", "+8 away unanswered"),
        EventDef("home_star_out", "Home star leaves / fouls out", "Lineup", "Home lineup strength −0.25"),
        EventDef("away_star_out", "Opponent star leaves / fouls out", "Lineup", "Away lineup strength −0.25"),
        EventDef("quiet_2", "2 scoreless minutes", "Time", "Clock runs 120s, no points"),
    ]
    actions = [
        ActionDef("push_pace", "Push pace & shoot more threes", "Higher tempo and three-point volume (higher variance)"),
        ActionDef("balanced", "Stay balanced", "Keep the current approach"),
        ActionDef("slow_down", "Slow down & work inside", "Lower tempo, fewer threes, more control"),
    ]
    TAC = {"push_pace": (0.12, 0.08), "balanced": (0.0, 0.0), "slow_down": (-0.12, -0.08)}

    def features(self, s):
        return basketball_features(s)

    def terminal(self, s):
        if s["elapsed_sec"] >= GAME_SEC:
            if s["home_score"] == s["away_score"]:
                return [0.5, 0.5]
            return [0.0, 1.0] if s["home_score"] > s["away_score"] else [1.0, 0.0]
        return None

    def focus_name(self, s):
        return s["home_team"]

    def outcome_labels(self, s):
        return [s["away_team"], s["home_team"]]

    def scoreboard(self, s):
        q, c = clock(s["elapsed_sec"])
        fin = s["elapsed_sec"] >= GAME_SEC
        return dict(teams=[dict(name=s["home_team"], score=str(s["home_score"]), sub="home", active=True),
                           dict(name=s["away_team"], score=str(s["away_score"]), sub="away", active=True)],
                    status="Final" if fin else "Live (simulated replay)", clock="FINAL" if fin else f"Q{q} {c}",
                    venue=f"{s['home_team']} arena", phase=f"Quarter {q}")

    def momentum(self, s):
        f = basketball_features(s)
        d5 = s["recent_points_home"] - s["recent_points_away"]
        parts = [
            MomentumPart("Last-5-minute scoring", 0.40, d5 / 8.0, f"last 5 min {s['recent_points_home']}–{s['recent_points_away']}"),
            MomentumPart("Current scoring run", 0.25, s["current_run"] / 8.0,
                         f"{abs(s['current_run'])}-0 run for {s['home_team'] if s['current_run'] > 0 else s['away_team']}" if s["current_run"] else "no active run"),
            MomentumPart("Possession efficiency", 0.20, f["eff_diff"] / 0.2, f"points/possession edge {f['eff_diff']:+.2f}"),
            MomentumPart("Ball security", 0.10, (s["away_tov"] - s["home_tov"]) / 4.0, f"turnovers {s['home_tov']}–{s['away_tov']}"),
            MomentumPart("Foul trouble", 0.05, (s["away_fouls"] - s["home_fouls"]) / 5.0, f"team fouls {s['home_fouls']}–{s['away_fouls']}"),
        ]
        return momentum_from_parts(parts, s["home_team"],
                                   "M = 50 + 50·tanh(Σ wᵢ·zᵢ) for the HOME side: last-5-min point differential, active run, "
                                   "points-per-possession edge, turnovers and fouls.")

    def insights(self, s, f, probs, mom):
        out = []
        q, c = clock(s["elapsed_sec"])
        out.append(f"{s['home_team']} {s['home_score']}–{s['away_score']} {s['away_team']} (Q{q} {c}).")
        if s["current_run"] and abs(s["current_run"]) >= 6:
            who = s["home_team"] if s["current_run"] > 0 else s["away_team"]
            out.append(f"{who} are on a {abs(s['current_run'])}-0 run; a timeout is the standard counter.")
        if f["fg_pct_diff"] > 0.05 or f["fg_pct_diff"] < -0.05:
            who = s["home_team"] if f["fg_pct_diff"] > 0 else s["away_team"]
            out.append(f"{who} hold a clear shooting edge ({abs(f['fg_pct_diff']) * 100:.0f} points of FG%), though shooting percentages regress.")
        if abs(s["home_tov"] - s["away_tov"]) >= 4:
            who = s["away_team"] if s["home_tov"] > s["away_tov"] else s["home_team"]
            out.append(f"{who} are converting turnovers into extra possessions.")
        if s["elapsed_sec"] > GAME_SEC - 360 and abs(s["home_score"] - s["away_score"]) <= 8:
            out.append("Clutch time: fouls, free throws and shot selection decide close games from here.")
        out.append(f"Momentum for {s['home_team']}: {mom['score']:.0f}/100 ({mom['label'].lower()}).")
        return out

    # ------------------------------------------------------------ what-if
    @staticmethod
    def _score(s, side, pts, three):
        o = "away" if side == "home" else "home"
        s[f"{side}_fga"] += 1
        s[f"{side}_fgm"] += 1
        if three:
            s[f"{side}_3pa"] += 1
            s[f"{side}_3pm"] += 1
            s[f"{side}_ast"] += 1
        s[f"{side}_score"] += pts
        s["elapsed_sec"] = min(GAME_SEC, s["elapsed_sec"] + 15)
        s["possession"] = 1 if side == "home" else 0
        s[f"recent_points_{side}"] = min(60, s[f"recent_points_{side}"] + pts)
        sg = 1 if side == "home" else -1
        s["current_run"] = max(-40, min(40, s["current_run"] + sg * pts if s["current_run"] * sg > 0 else sg * pts))
        _ = o

    def apply_event(self, state, event_id):
        s = copy.deepcopy(state)
        if event_id in ("home_three", "away_three"):
            self._score(s, event_id.split("_")[0], 3, True)
        elif event_id in ("home_two", "away_two"):
            self._score(s, event_id.split("_")[0], 2, False)
        elif event_id in ("home_turnover", "away_turnover"):
            side = event_id.split("_")[0]
            s[f"{side}_tov"] += 1
            s["elapsed_sec"] = min(GAME_SEC, s["elapsed_sec"] + 15)
            s["possession"] = 1 if side == "away" else 0
        elif event_id in ("home_run", "away_run"):
            side = event_id.split("_")[0]
            for pts, three in ((3, True), (2, False), (3, True)):
                self._score(s, side, pts, three)
        elif event_id == "home_star_out":
            s["home_lineup"] = max(-1.0, s["home_lineup"] - 0.25)
        elif event_id == "away_star_out":
            s["away_lineup"] = max(-1.0, s["away_lineup"] - 0.25)
        elif event_id == "quiet_2":
            s["elapsed_sec"] = min(GAME_SEC, s["elapsed_sec"] + 120)
            s["recent_points_home"] = int(round(s["recent_points_home"] * 0.6))
            s["recent_points_away"] = int(round(s["recent_points_away"] * 0.6))
            s["current_run"] = int(s["current_run"] * 0.5)
        else:
            raise KeyError(event_id)
        return s

    # ------------------------------------------------------------ coach
    def coach_sides(self, state):
        return ["home", "away"]

    def rollout(self, state, action_id, rng, n, side="home"):
        D = 0.6 * (state["home_elo"] - state["away_elo"]) / 100.0
        pace, three = self.TAC[action_id]
        out = []
        for _ in range(n):
            st = copy.deepcopy(state)
            sim.advance(st, rng, 300, D, pace=pace, three=three, tac_side=side)
            out.append(st)
        return out

    def rollout_stats(self, state, rolled, side):
        n, me, op = len(rolled), side, "away" if side == "home" else "home"
        return {"points scored": sum(r[f"{me}_score"] - state[f"{me}_score"] for r in rolled) / n,
                "points allowed": sum(r[f"{op}_score"] - state[f"{op}_score"] for r in rolled) / n}

    def coach_value(self, probs, side):
        return float(probs[1]) if side == "home" else float(probs[0])

    def coach_text(self, state, best, values, side, mom):
        team = state["home_team"] if side == "home" else state["away_team"]
        q, c = clock(state["elapsed_sec"])
        m = mom["score"] if side == "home" else 100 - mom["score"]
        margin = state["home_score"] - state["away_score"]
        margin = margin if side == "home" else -margin
        return dict(situation=f"{team} are {'up' if margin > 0 else 'down' if margin < 0 else 'level'} "
                             f"{abs(margin)} in Q{q} {c}; momentum {m:.0f}/100.", side=team)
