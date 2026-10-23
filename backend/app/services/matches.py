"""Match timelines: per-step predictions/momentum and on-pitch player cards."""
from __future__ import annotations

from collections import defaultdict

from app.models_db import Match
from app.services.analysis import analyze, predict_state
from app.sports.registry import get_adapter


def clean_state(raw: dict) -> dict:
    return {k: v for k, v in raw.items() if k not in ("step_label",)}


_CACHE: dict[int, dict] = {}


def match_series(m: Match) -> dict:
    """Probabilities + momentum for every step of the timeline (cached per match)."""
    if m.id in _CACHE:
        return _CACHE[m.id]
    a = get_adapter(m.sport)
    steps = []
    for i, raw in enumerate(m.timeline):
        st = a.validate(clean_state(raw))
        pred = predict_state(m.sport, st)
        mom = a.momentum(st)
        sb = a.scoreboard(st)
        steps.append(dict(i=i, label=raw.get("step_label", str(i)), probs=pred["probs"], lo=pred["lo"], hi=pred["hi"],
                          terminal=pred["terminal"], momentum=mom["score"], clock=sb["clock"],
                          score=[t["score"] for t in sb["teams"]]))
    out = dict(match_id=m.id, sport=m.sport, steps=steps, classes=a.outcome_labels(a.validate(clean_state(m.timeline[0]))),
               focus_class=a.focus_class)
    _CACHE[m.id] = out
    return out


def step_analysis(m: Match, k: int, target_class: int | None = None) -> dict:
    if not 0 <= k < len(m.timeline):
        raise IndexError(k)
    res = analyze(m.sport, clean_state(m.timeline[k]), explain=True, target_class=target_class)
    res["step"] = dict(i=k, n=len(m.timeline), label=m.timeline[k].get("step_label", str(k)))
    res["key_players"] = key_players(m, k)
    return res


def match_card(m: Match) -> dict:
    return dict(id=m.id, sport=m.sport, slug=m.slug, title=m.title, home=m.home, away=m.away, venue=m.venue,
                status=m.status, n_steps=len(m.timeline), result=m.meta.get("result"))


# ------------------------------------------------------------------------------------ key players
def key_players(m: Match, k: int) -> list[dict]:
    st = m.timeline[k]
    ev = m.events
    if m.sport == "cricket":
        return _cricket_players(m, st, ev)
    if m.sport == "football":
        return _football_players(m, st, ev)
    return _basketball_players(m, st, ev)


def _cricket_players(m, st, ev):
    inn, bb = st["innings"], st["balls_bowled"]
    seen = [e for e in ev if e["inn"] < inn or (e["inn"] == inn and e["over"] * 6 + e["ball"] < bb)]
    bat, bowl = defaultdict(lambda: dict(runs=0, balls=0, fours=0, sixes=0, out=False)), defaultdict(lambda: dict(balls=0, runs=0, wkts=0))
    for e in seen:
        b = bat[(e["inn"], e["striker"])]
        b["runs"] += e["runs"]
        b["balls"] += 1
        b["fours"] += e["runs"] == 4
        b["sixes"] += e["runs"] == 6
        b["out"] |= bool(e["wicket"])
        w = bowl[(e["inn"], e["bowler"])]
        w["balls"] += 1
        w["runs"] += e["runs"]
        w["wkts"] += e["wicket"]
    out = []
    cur = sorted([(n, v) for (i, n), v in bat.items() if i == inn], key=lambda t: -t[1]["runs"])[:3]
    for n, v in cur:
        out.append(dict(name=n, team=st["batting_team"], role="Batter", headline=f"{v['runs']} ({v['balls']})",
                        detail=f"{v['fours']}×4  {v['sixes']}×6  SR {100 * v['runs'] / max(v['balls'], 1):.0f}" + ("  · out" if v["out"] else "  · batting"),
                        value=v["runs"]))
    cb = sorted([(n, v) for (i, n), v in bowl.items() if i == inn], key=lambda t: (-t[1]["wkts"], t[1]["runs"] / max(t[1]["balls"], 1)))[:2]
    for n, v in cb:
        out.append(dict(name=n, team=st["bowling_team"], role="Bowler", headline=f"{v['wkts']}/{v['runs']}",
                        detail=f"{v['balls'] // 6}.{v['balls'] % 6} ov  econ {6 * v['runs'] / max(v['balls'], 1):.1f}", value=v["wkts"] * 10))
    return out


def _football_players(m, st, ev):
    seen = [e for e in ev if e["minute"] <= st["minute"]]
    agg: dict = defaultdict(lambda: dict(goals=0, assists=0, shots=0, xg=0.0, cards=0, team=""))
    for e in seen:
        if e["type"] == "shot":
            p = agg[e["player"]]
            p["team"] = e["team"]
            p["shots"] += 1
            p["xg"] += e["xg"]
            p["goals"] += e["goal"]
            if e.get("assist"):
                agg[e["assist"]]["assists"] += 1
                agg[e["assist"]]["team"] = e["team"]
        elif e["type"] in ("yellow", "red"):
            agg[e["player"]]["cards"] += 1
            agg[e["player"]]["team"] = e["team"]
    rows = sorted(agg.items(), key=lambda t: (-(t[1]["goals"] * 3 + t[1]["assists"] * 2 + t[1]["xg"]), t[0]))[:5]
    return [dict(name=n, team=v["team"], role="Player", headline=f"{v['goals']}G {v['assists']}A",
                 detail=f"{v['shots']} shots · {v['xg']:.2f} xG" + (f" · {v['cards']} card" if v["cards"] else ""),
                 value=v["goals"] * 3 + v["assists"] * 2 + v["xg"]) for n, v in rows]


def _basketball_players(m, st, ev):
    seen = [e for e in ev if e["t"] <= st["elapsed_sec"]]
    agg: dict = defaultdict(lambda: dict(pts=0, reb=0, ast=0, team=""))
    for e in seen:
        if e["type"] in ("shot", "ft", "tov"):
            p = agg[e["player"]]
            p["team"] = e["team"]
            if e["type"] == "shot":
                p["pts"] += e["pts"] if e["made"] else 0
                if e.get("assist"):
                    agg[e["assist"]]["ast"] += 1
                    agg[e["assist"]]["team"] = e["team"]
                if e.get("rebound"):
                    agg[e["rebound"]]["reb"] += 1
                    agg[e["rebound"]]["team"] = m.home if e["rebound_side"] == "home" else m.away
            elif e["type"] == "ft":
                p["pts"] += e["pts"]
    rows = sorted(agg.items(), key=lambda t: (-t[1]["pts"], t[0]))[:5]
    return [dict(name=n, team=v["team"], role="Player", headline=f"{v['pts']} pts",
                 detail=f"{v['reb']} reb · {v['ast']} ast", value=v["pts"]) for n, v in rows]
