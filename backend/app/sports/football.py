"""Football adapter. Outcomes: home win / draw / away win. Momentum is expressed for the home side."""
from __future__ import annotations

import copy

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.sports.base import ActionDef, EventDef, FeatureMeta, MomentumPart, SportAdapter, momentum_from_parts
from app.sports.features import football_features
from app.synth import football as sim


class FootballState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    home_team: str = Field("North Quay", max_length=40)
    away_team: str = Field("Red Harbour", max_length=40)
    minute: int = Field(0, ge=0, le=90)
    home_goals: int = Field(0, ge=0, le=20)
    away_goals: int = Field(0, ge=0, le=20)
    home_shots: int = Field(0, ge=0, le=60)
    away_shots: int = Field(0, ge=0, le=60)
    home_sot: int = Field(0, ge=0, le=40)
    away_sot: int = Field(0, ge=0, le=40)
    home_xg: float = Field(0.0, ge=0, le=12)
    away_xg: float = Field(0.0, ge=0, le=12)
    home_possession: float = Field(50.0, ge=0, le=100)
    home_corners: int = Field(0, ge=0, le=30)
    away_corners: int = Field(0, ge=0, le=30)
    home_fouls: int = Field(0, ge=0, le=40)
    away_fouls: int = Field(0, ge=0, le=40)
    home_yellow: int = Field(0, ge=0, le=11)
    away_yellow: int = Field(0, ge=0, le=11)
    home_red: int = Field(0, ge=0, le=4)
    away_red: int = Field(0, ge=0, le=4)
    home_pass_acc: float = Field(80.0, ge=40, le=100)
    away_pass_acc: float = Field(80.0, ge=40, le=100)
    home_elo: float = Field(1500.0, ge=1000, le=2000)
    away_elo: float = Field(1500.0, ge=1000, le=2000)
    home_lineup: float = Field(0.0, ge=-1.0, le=0.0)
    away_lineup: float = Field(0.0, ge=-1.0, le=0.0)
    recent_shots_home: int = Field(0, ge=0, le=30)
    recent_shots_away: int = Field(0, ge=0, le=30)
    recent_xg_home: float = Field(0.0, ge=0, le=6)
    recent_xg_away: float = Field(0.0, ge=0, le=6)
    recent_goals_home: int = Field(0, ge=0, le=8)
    recent_goals_away: int = Field(0, ge=0, le=8)

    @model_validator(mode="after")
    def _consistent(self):
        for side in ("home", "away"):
            shots, sot, goals = getattr(self, f"{side}_shots"), getattr(self, f"{side}_sot"), getattr(self, f"{side}_goals")
            if sot > shots:
                raise ValueError(f"{side}_sot cannot exceed {side}_shots")
            if goals > sot:
                raise ValueError(f"{side}_goals cannot exceed {side}_sot")
        return self


class FootballAdapter(SportAdapter):
    key = "football"
    name = "Football"
    tagline = "xG, shot maps & three-way win probability"
    classes = ["Home win", "Draw", "Away win"]
    focus_class = 0
    state_model = FootballState
    analytics = ["Win / draw / loss probability", "Momentum", "xG timeline", "Shot map", "Possession",
                 "Team comparison", "Player predictions", "What-if simulation", "AI Coach"]
    coach_horizon = "next 15 minutes"
    feature_meta = {
        "minute": FeatureMeta("Match minute", 0, "{:.0f}"), "minutes_remaining": FeatureMeta("Minutes remaining", 0, "{:.0f}"),
        "goal_diff": FeatureMeta("Goal difference", 1, "{:+.0f}"), "home_goals": FeatureMeta("Home goals", 1, "{:.0f}"),
        "away_goals": FeatureMeta("Away goals", -1, "{:.0f}"), "lead_security": FeatureMeta("Lead vs time left", 1, "{:+.2f}"),
        "shots_diff": FeatureMeta("Shot difference", 1, "{:+.0f}"), "sot_diff": FeatureMeta("Shots-on-target difference", 1, "{:+.0f}"),
        "xg_diff": FeatureMeta("xG difference", 1, "{:+.2f}"), "home_possession": FeatureMeta("Home possession", 1, "{:.0f}", "%"),
        "corners_diff": FeatureMeta("Corner difference", 1, "{:+.0f}"), "fouls_diff": FeatureMeta("Foul difference", -1, "{:+.0f}"),
        "yellow_diff": FeatureMeta("Yellow-card difference", -1, "{:+.0f}"), "red_diff": FeatureMeta("Red-card difference", -1, "{:+.0f}"),
        "pass_acc_diff": FeatureMeta("Pass-accuracy difference", 1, "{:+.1f}", "pp"),
        "elo_diff": FeatureMeta("Pre-match rating gap", 1, "{:+.2f}"), "lineup_diff": FeatureMeta("Lineup strength gap", 1, "{:+.2f}"),
    }
    phrases = {
        "goal_diff": ("Leading on the scoreboard", "Trailing on the scoreboard"),
        "lead_security": ("The lead is hard to overturn with this time left", "The deficit is large relative to time left"),
        "home_goals": ("Home goals scored so far", "Few home goals scored so far"),
        "away_goals": ("Away side has not scored much", "Away goals keep them in it"),
        "xg_diff": ("Creating the better chances (xG {xg_diff:+.2f})", "Being out-created on chances (xG {xg_diff:+.2f})"),
        "shots_diff": ("Out-shooting the opponent ({shots_diff:+.0f})", "Being out-shot ({shots_diff:+.0f})"),
        "sot_diff": ("More shots on target ({sot_diff:+.0f})", "Fewer shots on target ({sot_diff:+.0f})"),
        "home_possession": ("Controlling possession ({v:.0f}%)", "Ceding possession ({v:.0f}%)"),
        "red_diff": ("Playing with a numerical advantage", "Playing with a numerical disadvantage"),
        "elo_diff": ("Stronger side on pre-match rating", "Weaker side on pre-match rating"),
        "lineup_diff": ("Lineup is at full strength vs opponent", "Key player missing from the lineup"),
        "minutes_remaining": ("Plenty of time left to extend", "Little time left to change the outcome"),
        "minute": ("Match stage favours home", "Match stage favours the opponent"),
        "corners_diff": ("More corners won", "Fewer corners won"),
        "fouls_diff": ("Fewer fouls conceded", "More fouls conceded"),
        "yellow_diff": ("Fewer bookings", "More bookings"),
        "pass_acc_diff": ("Cleaner passing", "Sloppier passing"),
    }
    events = [
        EventDef("home_goal", "Home goal", "Goals", "+1 home goal (0.35 xG shot)"),
        EventDef("away_goal", "Away goal", "Goals", "+1 away goal (0.35 xG shot)"),
        EventDef("home_red", "Home red card", "Discipline", "Home down to 10"),
        EventDef("away_red", "Away red card", "Discipline", "Away down to 10"),
        EventDef("home_striker_out", "Home key striker substituted / injured", "Lineup", "Home lineup strength −0.22"),
        EventDef("away_striker_out", "Away key striker substituted / injured", "Lineup", "Away lineup strength −0.22"),
        EventDef("home_pressure", "Home sustained pressure", "Chances", "+5 shots, +2 SoT, +0.6 xG, +2 corners"),
        EventDef("away_pressure", "Away sustained pressure", "Chances", "+5 shots, +2 SoT, +0.6 xG, +2 corners"),
        EventDef("quiet_10", "10 quiet minutes", "Time", "Clock runs 10 min with no events"),
    ]
    actions = [
        ActionDef("push_forward", "Push forward (high press)", "More attacking volume, more exposure at the back"),
        ActionDef("balanced", "Stay balanced", "Keep the current approach"),
        ActionDef("protect", "Defend / protect the result", "Fewer chances either way, lower tempo"),
    ]
    TAC = {"push_forward": 0.30, "balanced": 0.0, "protect": -0.30}

    def features(self, s):
        return football_features(s)

    def terminal(self, s):
        if s["minute"] >= 90:
            gd = s["home_goals"] - s["away_goals"]
            return [1.0, 0.0, 0.0] if gd > 0 else ([0.0, 0.0, 1.0] if gd < 0 else [0.0, 1.0, 0.0])
        return None

    def focus_name(self, s):
        return s["home_team"]

    def outcome_labels(self, s):
        return [s["home_team"], "Draw", s["away_team"]]

    def scoreboard(self, s):
        ft = s["minute"] >= 90
        return dict(teams=[dict(name=s["home_team"], score=str(s["home_goals"]), sub="home", active=True),
                           dict(name=s["away_team"], score=str(s["away_goals"]), sub="away", active=True)],
                    status="Full time" if ft else "Live (simulated replay)", clock="FT" if ft else f"{s['minute']}'",
                    venue=f"{s['home_team']} home ground",
                    phase="Second half" if s["minute"] > 45 else "First half")

    def momentum(self, s):
        dxg = s["recent_xg_home"] - s["recent_xg_away"]
        dsh = s["recent_shots_home"] - s["recent_shots_away"]
        dgl = s["recent_goals_home"] - s["recent_goals_away"]
        parts = [
            MomentumPart("Chance quality (last 15 min)", 0.35, dxg / 0.8, f"recent xG {s['recent_xg_home']:.2f} vs {s['recent_xg_away']:.2f}"),
            MomentumPart("Goals (last 15 min)", 0.25, float(dgl), f"recent goals {s['recent_goals_home']}–{s['recent_goals_away']}"),
            MomentumPart("Shot volume (last 15 min)", 0.15, dsh / 5.0, f"recent shots {s['recent_shots_home']}–{s['recent_shots_away']}"),
            MomentumPart("Possession tilt", 0.10, (s["home_possession"] - 50) / 10.0, f"home possession {s['home_possession']:.0f}%"),
            MomentumPart("Numerical advantage", 0.15, (s["away_red"] - s["home_red"]) * 1.5, f"red cards {s['home_red']}–{s['away_red']}"),
        ]
        return momentum_from_parts(parts, s["home_team"],
                                   "M = 50 + 50·tanh(Σ wᵢ·zᵢ) for the HOME side over a 15-minute window of xG, goals, shots, "
                                   "possession and red cards; 50 is balanced.")

    def insights(self, s, f, probs, mom):
        out = []
        h, a = s["home_team"], s["away_team"]
        out.append(f"{h} {s['home_goals']}–{s['away_goals']} {a} after {s['minute']}'; xG {s['home_xg']:.2f}–{s['away_xg']:.2f}.")
        gd = s["home_goals"] - s["away_goals"]
        if abs(s["home_xg"] - s["away_xg"] - gd) > 0.9 and s["minute"] >= 30:
            under = h if (s["home_xg"] - s["home_goals"]) > (s["away_xg"] - s["away_goals"]) else a
            out.append(f"The scoreline understates {under}'s chances; regression to xG suggests they are due.")
        out.append(f"Momentum for {h}: {mom['score']:.0f}/100 ({mom['label'].lower()}).")
        if s["home_red"] or s["away_red"]:
            out.append("A red card is reshaping the game: the side with 11 players gains chance volume.")
        if s["minute"] >= 70 and gd != 0:
            out.append(f"With {90 - s['minute']} minutes left, the {'leader' if gd else ''} is managing the game; late goals are the main swing risk.")
        if s["home_lineup"] < 0 or s["away_lineup"] < 0:
            out.append("A key player is missing from at least one lineup, lowering that side's chance creation.")
        return out

    # --------------------------------------------------------------- what-if
    def apply_event(self, state, event_id):
        s = copy.deepcopy(state)
        def goal(side):
            s[f"{side}_goals"] += 1
            s[f"{side}_shots"] += 1
            s[f"{side}_sot"] += 1
            s[f"{side}_xg"] = round(s[f"{side}_xg"] + 0.35, 3)
            s[f"recent_goals_{side}"] += 1
            s[f"recent_shots_{side}"] += 1
            s[f"recent_xg_{side}"] = round(s[f"recent_xg_{side}"] + 0.35, 3)
        def pressure(side):
            s[f"{side}_shots"] += 5
            s[f"{side}_sot"] += 2
            s[f"{side}_xg"] = round(s[f"{side}_xg"] + 0.6, 3)
            s[f"{side}_corners"] += 2
            s[f"recent_shots_{side}"] += 5
            s[f"recent_xg_{side}"] = round(s[f"recent_xg_{side}"] + 0.6, 3)
        if event_id == "home_goal":
            goal("home")
        elif event_id == "away_goal":
            goal("away")
        elif event_id == "home_red":
            s["home_red"] += 1
        elif event_id == "away_red":
            s["away_red"] += 1
        elif event_id == "home_striker_out":
            s["home_lineup"] = max(-1.0, s["home_lineup"] - 0.22)
        elif event_id == "away_striker_out":
            s["away_lineup"] = max(-1.0, s["away_lineup"] - 0.22)
        elif event_id == "home_pressure":
            pressure("home")
        elif event_id == "away_pressure":
            pressure("away")
        elif event_id == "quiet_10":
            s["minute"] = min(90, s["minute"] + 10)
            for k in ("recent_shots_home", "recent_shots_away", "recent_goals_home", "recent_goals_away"):
                s[k] = int(round(s[k] * 0.33))
            s["recent_xg_home"] = round(s["recent_xg_home"] * 0.33, 3)
            s["recent_xg_away"] = round(s["recent_xg_away"] * 0.33, 3)
        else:
            raise KeyError(event_id)
        for side in ("home", "away"):
            s[f"{side}_sot"] = min(s[f"{side}_sot"], s[f"{side}_shots"])
        return s

    # --------------------------------------------------------------- coach
    def coach_sides(self, state):
        return ["home", "away"]

    def rollout(self, state, action_id, rng, n, side="home"):
        D = 0.6 * (state["home_elo"] - state["away_elo"]) / 100.0
        tac = self.TAC[action_id]
        out = []
        for _ in range(n):
            st = copy.deepcopy(state)
            sim.advance(st, rng, 15, D, tac if side == "home" else 0.0, tac if side == "away" else 0.0)
            out.append(st)
        return out

    coach_metric = "expected points"

    def rollout_stats(self, state, rolled, side):
        n, me, op = len(rolled), side, "away" if side == "home" else "home"
        return {"goals for": sum(r[f"{me}_goals"] - state[f"{me}_goals"] for r in rolled) / n,
                "goals against": sum(r[f"{op}_goals"] - state[f"{op}_goals"] for r in rolled) / n,
                "xG created": sum(r[f"{me}_xg"] - state[f"{me}_xg"] for r in rolled) / n,
                "xG conceded": sum(r[f"{op}_xg"] - state[f"{op}_xg"] for r in rolled) / n}

    def coach_value(self, probs, side):
        """Expected league points for the side (3·P(win) + 1·P(draw))."""
        return float(3 * probs[0] + probs[1]) if side == "home" else float(3 * probs[2] + probs[1])

    def coach_text(self, state, best, values, side, mom):
        team = state["home_team"] if side == "home" else state["away_team"]
        gd = state["home_goals"] - state["away_goals"]
        gd = gd if side == "home" else -gd
        status = "leading" if gd > 0 else ("trailing" if gd < 0 else "level")
        m = mom["score"] if side == "home" else 100 - mom["score"]
        return dict(situation=f"{team} are {status} ({state['home_goals']}–{state['away_goals']}) in minute {state['minute']} "
                             f"with momentum {m:.0f}/100.", side=team)
