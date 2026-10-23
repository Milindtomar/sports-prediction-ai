"""Cricket (T20) adapter - the flagship sport.

Headline probability = P(current batting side wins). Innings 1 and 2 share one model;
in innings 1 the "target" feature is replaced by the venue par score (see features.py).
"""
from __future__ import annotations

import copy
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.sports.base import ActionDef, EventDef, FeatureMeta, MomentumPart, SportAdapter, momentum_from_parts
from app.sports.features import cricket_features
from app.synth import cricket as sim


class CricketState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    innings: Literal[1, 2] = 2
    batting_team: str = Field("Harbor Kings", max_length=40)
    bowling_team: str = Field("Crimson Falcons", max_length=40)
    venue: str = Field("Harbour Oval", max_length=60)
    runs: int = Field(0, ge=0, le=400)
    wickets: int = Field(0, ge=0, le=10)
    balls_bowled: int = Field(0, ge=0, le=120)
    target: Optional[int] = Field(None, ge=1, le=400)
    partnership_runs: int = Field(0, ge=0, le=250)
    partnership_balls: int = Field(0, ge=0, le=120)
    recent_runs: int = Field(0, ge=0, le=72)
    recent_wickets: int = Field(0, ge=0, le=12)
    recent_boundaries: int = Field(0, ge=0, le=12)
    batting_elo: float = Field(1500.0, ge=1000, le=2000)
    bowling_elo: float = Field(1500.0, ge=1000, le=2000)
    venue_par: Optional[int] = Field(None, ge=80, le=260)

    @model_validator(mode="after")
    def _consistent(self):
        if self.innings == 2 and self.target is None:
            raise ValueError("target is required in innings 2")
        if self.partnership_balls > self.balls_bowled:
            raise ValueError("partnership_balls cannot exceed balls_bowled")
        if self.partnership_runs > self.runs:
            raise ValueError("partnership_runs cannot exceed runs")
        if self.recent_runs > self.runs:
            raise ValueError("recent_runs cannot exceed runs")
        if self.recent_wickets > self.wickets:
            raise ValueError("recent_wickets cannot exceed wickets")
        if self.batting_team.strip().lower() == self.bowling_team.strip().lower():
            raise ValueError("batting_team and bowling_team must differ")
        if self.venue not in sim.VENUES:
            raise ValueError(f"unknown venue '{self.venue}'; choose one of {', '.join(sim.VENUES)}")
        if self.innings == 1:
            self.target = None
        if self.venue_par is None:
            self.venue_par = sim.VENUES.get(self.venue, (1.0, 158))[1]
        return self


def overs_str(balls: int) -> str:
    return f"{balls // 6}.{balls % 6}"


class CricketAdapter(SportAdapter):
    key = "cricket"
    name = "Cricket"
    tagline = "T20 chase & defence analytics"
    classes = ["Bowling side wins", "Batting side wins"]
    focus_class = 1
    state_model = CricketState
    analytics = ["Win probability", "Momentum", "Run-rate trend", "Partnership analysis", "Wagon wheel",
                 "Pitch map", "Player predictions", "What-if simulation", "AI Coach"]
    coach_horizon = "next 2 overs (12 balls)"
    feature_meta = {
        "innings": FeatureMeta("Innings", 0, "{:.0f}"), "runs": FeatureMeta("Runs scored", 0, "{:.0f}"),
        "wickets_remaining": FeatureMeta("Wickets in hand", 1, "{:.0f}"),
        "balls_remaining": FeatureMeta("Balls remaining", 0, "{:.0f}"),
        "crr": FeatureMeta("Current run rate", 1, "{:.2f}", "rpo"), "runs_required": FeatureMeta("Runs still needed", -1, "{:.0f}"),
        "rrr": FeatureMeta("Required run rate", -1, "{:.2f}", "rpo"), "rr_diff": FeatureMeta("Run-rate margin (CRR − RRR)", 1, "{:+.2f}"),
        "recent_rr": FeatureMeta("Scoring rate, last 2 overs", 1, "{:.2f}", "rpo"),
        "recent_wickets": FeatureMeta("Wickets, last 2 overs", -1, "{:.0f}"),
        "partnership_runs": FeatureMeta("Current partnership", 1, "{:.0f}"),
        "resources": FeatureMeta("Batting resources left", 1, "{:.0%}"),
        "elo_diff": FeatureMeta("Pre-match rating gap", 1, "{:+.2f}"), "venue_par": FeatureMeta("Venue par score", 0, "{:.0f}"),
        "phase": FeatureMeta("Match phase", 0, "{:.0f}"),
    }
    phrases = {
        "wickets_remaining": ("{v:.0f} wickets in hand give licence to attack", "Only {v:.0f} wickets in hand limit risk-taking"),
        "rrr": ("Required rate is manageable at {v:.1f} an over", "Required rate has climbed to {v:.1f} an over"),
        "crr": ("Scoring at a healthy {v:.1f} an over", "Scoring at {v:.1f} an over is below what is needed"),
        "rr_diff": ("Scoring {v:+.1f} an over faster than required", "Scoring {v:+.1f} an over versus the required rate"),
        "recent_rr": ("Last two overs went at {v:.1f} an over", "Last two overs only managed {v:.1f} an over"),
        "recent_wickets": ("No recent wicket pressure on the batters", "{v:.0f} wicket(s) in the last two overs hurt"),
        "partnership_runs": ("Settled partnership of {v:.0f}", "New partnership - only {v:.0f} runs so far"),
        "resources": ("Plenty of batting resources left ({v:.0%})", "Few batting resources left ({v:.0%})"),
        "runs_required": ("Only {v:.0f} runs still needed", "{v:.0f} runs still needed"),
        "balls_remaining": ("{v:.0f} balls left to work with", "Only {v:.0f} balls left"),
        "elo_diff": ("Stronger side on pre-match rating", "Weaker side on pre-match rating"),
        "venue_par": ("Conditions suit the batting side", "Conditions suit the bowling side"),
        "runs": ("Runs on the board help", "Runs on the board are short of par"),
        "innings": ("Batting second means a known target", "Batting first leaves the target unknown"),
        "phase": ("This phase favours the batting side", "This phase favours the bowling side"),
    }
    events = [
        EventDef("dot", "Dot ball", "Next ball", "0 runs"), EventDef("single", "Single", "Next ball", "1 run"),
        EventDef("four", "FOUR", "Next ball", "Boundary"), EventDef("six", "SIX", "Next ball", "Maximum"),
        EventDef("wicket", "WICKET", "Next ball", "Batter dismissed"),
        EventDef("maiden", "Maiden over", "Next over", "6 dot balls"),
        EventDef("big_over", "18-run over", "Next over", "6,4,2,4,0,2"),
        EventDef("two_wickets", "2 wickets in the over", "Next over", "Collapse"),
        EventDef("flat_pitch", "Pitch plays flatter", "Conditions", "Venue par +12 runs"),
        EventDef("slow_pitch", "Pitch slows / grips", "Conditions", "Venue par −12 runs"),
    ]
    actions = [
        ActionDef("attack", "Increase attacking intent", "Raise batting aggression ~30% for the next two overs"),
        ActionDef("maintain", "Maintain current tempo", "Keep the current (rate-driven) batting approach"),
        ActionDef("consolidate", "Consolidate & protect wickets", "Lower aggression ~22% to preserve wickets"),
    ]

    # ------------------------------------------------------------------ basics
    def default_state(self):
        return self.validate(dict(innings=2, target=172, runs=118, wickets=4, balls_bowled=90, partnership_runs=32,
                                  partnership_balls=22, recent_runs=17, recent_wickets=0, recent_boundaries=2))

    def features(self, s):
        return cricket_features(s)

    def terminal(self, s):
        if s["innings"] != 2:
            return None
        if s["runs"] >= s["target"]:
            return [0.0, 1.0]
        if s["wickets"] >= 10 or s["balls_bowled"] >= 120:
            return [0.5, 0.5] if s["runs"] == s["target"] - 1 else [1.0, 0.0]
        return None

    def focus_name(self, s):
        return s["batting_team"]

    def outcome_labels(self, s):
        return [f"{s['bowling_team']}", f"{s['batting_team']}"]

    def scoreboard(self, s):
        o = overs_str(s["balls_bowled"])
        cur = f"{s['runs']}/{s['wickets']}"
        if s["innings"] == 2:
            need = s["target"] - s["runs"]
            left = 120 - s["balls_bowled"]
            status = (f"Need {need} from {left} balls" if need > 0 and left > 0 and s["wickets"] < 10 else
                      f"{s['batting_team']} won" if need <= 0 else
                      "Tied" if need == 1 else f"{s['bowling_team']} won")
            teams = [dict(name=s["bowling_team"], score=f"{s['target'] - 1}", sub="20 ov", active=False),
                     dict(name=s["batting_team"], score=cur, sub=f"{o} ov", active=True)]
        else:
            status = f"{s['batting_team']} batting first"
            teams = [dict(name=s["batting_team"], score=cur, sub=f"{o} ov", active=True),
                     dict(name=s["bowling_team"], score="–", sub="yet to bat", active=False)]
        return dict(teams=teams, status=status, clock=f"Over {o}", venue=s["venue"], innings=s["innings"],
                    phase=["Powerplay", "Middle overs", "Death overs"][sim.phase_of(min(s["balls_bowled"], 119))])

    # ------------------------------------------------------------------ momentum
    def momentum(self, s):
        f = cricket_features(s)
        ph = sim.phase_of(min(s["balls_bowled"], 119))
        par_rate = s["venue_par"] / 20.0 * (0.95, 0.9, 1.25)[ph]
        tempo_z = (f["recent_rr"] - par_rate) / 3.0
        wk_z = -0.8 * s["recent_wickets"] + 0.3
        bd_z = (s["recent_boundaries"] - 2.2) / 2.0
        part_z = min(s["partnership_runs"], 60) / 30.0 - 0.5
        press_z = f["rr_diff"] / 3.0
        parts = [
            MomentumPart("Recent scoring tempo", 0.35, tempo_z, f"{f['recent_rr']:.1f} rpo in last 2 overs vs {par_rate:.1f} phase par"),
            MomentumPart("Wicket pressure", 0.28, wk_z, f"{s['recent_wickets']} wicket(s) in last 2 overs"),
            MomentumPart("Boundary hitting", 0.15, bd_z, f"{s['recent_boundaries']} boundaries in last 12 balls"),
            MomentumPart("Partnership stability", 0.10, part_z, f"{s['partnership_runs']} run partnership"),
            MomentumPart("Required-rate pressure" if s["innings"] == 2 else "Pace vs par", 0.12, press_z,
                         f"CRR {f['crr']:.1f} vs {'required' if s['innings'] == 2 else 'par'} {f['rrr']:.1f}"),
        ]
        return momentum_from_parts(parts, s["batting_team"],
                                   "M = 50 + 50·tanh(Σ wᵢ·zᵢ) over recent tempo, wickets, boundaries, partnership and required-rate pressure; "
                                   "factor points split (M−50) in proportion to wᵢ·zᵢ.")

    # ------------------------------------------------------------------ insights
    def insights(self, s, f, probs, mom):
        out = []
        left = 120 - s["balls_bowled"]
        if s["innings"] == 2:
            need = s["target"] - s["runs"]
            out.append(f"{s['batting_team']} need {max(need, 0)} from {left} balls (required {f['rrr']:.1f} vs current {f['crr']:.1f} an over).")
        else:
            out.append(f"At the current rate {s['batting_team']} are on course for about {round(f['crr'] * 20)} (venue par {s['venue_par']}).")
        out.append(f"Momentum {mom['score']:.0f}/100 - {mom['label'].lower()}" + (f"; top driver: {mom['factors'][0]['label'].lower()}." if mom["factors"] else "."))
        if s["wickets"] >= 7:
            out.append(f"Only {10 - s['wickets']} wickets in hand - tail-end risk is the main danger to the batting side.")
        elif s["partnership_runs"] >= 40:
            out.append(f"A {s['partnership_runs']}-run partnership is anchoring the innings; breaking it is the bowling side's priority.")
        if sim.phase_of(min(s["balls_bowled"], 119)) == 2:
            out.append("Death overs: boundary-hitting outcomes swing the win probability the most right now.")
        elif sim.phase_of(min(s["balls_bowled"], 119)) == 0:
            out.append("Powerplay: fielding restrictions favour intent, but early wickets are costly.")
        return out

    # ------------------------------------------------------------------ what-if events
    @staticmethod
    def _ball(s: dict, runs: int, wk: int) -> None:
        if s["balls_bowled"] >= 120 or s["wickets"] >= 10 or (s["innings"] == 2 and s["runs"] >= s["target"]):
            return
        s["balls_bowled"] += 1
        s["runs"] += runs
        s["wickets"] += wk
        if wk:
            s["partnership_runs"] = 0
            s["partnership_balls"] = 0
        else:
            s["partnership_runs"] = min(250, s["partnership_runs"] + runs)
            s["partnership_balls"] = min(s["balls_bowled"], s["partnership_balls"] + 1)
        b = 1 if runs >= 4 else 0
        s["recent_runs"] = min(72, int(round(s["recent_runs"] * 11 / 12 + runs)))
        s["recent_wickets"] = min(12, int(round(s["recent_wickets"] * 11 / 12 + wk)))
        s["recent_boundaries"] = min(12, int(round(s["recent_boundaries"] * 11 / 12 + b)))

    def apply_event(self, state, event_id):
        s = copy.deepcopy(state)
        seqs = {
            "dot": [(0, 0)], "single": [(1, 0)], "four": [(4, 0)], "six": [(6, 0)], "wicket": [(0, 1)],
            "maiden": [(0, 0)] * 6, "big_over": [(6, 0), (4, 0), (2, 0), (4, 0), (0, 0), (2, 0)],
            "two_wickets": [(1, 0), (0, 1), (0, 0), (0, 1), (1, 0), (0, 0)],
        }
        if event_id in seqs:
            for r, w in seqs[event_id]:
                self._ball(s, r, w)
        elif event_id == "flat_pitch":
            s["venue_par"] = min(260, s["venue_par"] + 12)
        elif event_id == "slow_pitch":
            s["venue_par"] = max(80, s["venue_par"] - 12)
        else:
            raise KeyError(event_id)
        return s

    # ------------------------------------------------------------------ AI coach
    MULT = {"attack": 1.30, "maintain": 1.0, "consolidate": 0.78}

    def rollout(self, state, action_id, rng, n, side="focus"):
        d = sim.D_PER_ELO100 * 0.6 * (state["batting_elo"] - state["bowling_elo"]) / 100.0
        vf = state["venue_par"] / 158.0
        out = []
        for _ in range(n):
            st = copy.deepcopy(state)
            sim.advance(st, rng, 12, d, vf, aggr_mult=self.MULT[action_id])
            out.append(st)
        return out

    def rollout_stats(self, state, rolled, side):
        n = len(rolled)
        return {"runs scored": sum(r["runs"] - state["runs"] for r in rolled) / n,
                "wickets lost": sum(r["wickets"] - state["wickets"] for r in rolled) / n}

    def coach_text(self, state, best, values, side, mom):
        f = cricket_features(state)
        who = state["batting_team"]
        if state["innings"] == 2:
            sit = (f"{who} need {state['target'] - state['runs']} from {120 - state['balls_bowled']} balls "
                   f"(required {f['rrr']:.1f} vs current {f['crr']:.1f}); momentum {mom['score']:.0f}/100.")
        else:
            sit = f"{who} are {state['runs']}/{state['wickets']} after {overs_str(state['balls_bowled'])} overs; momentum {mom['score']:.0f}/100."
        return dict(situation=sit, side=who)
