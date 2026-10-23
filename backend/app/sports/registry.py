"""Adapter registry - the single place a new sport is plugged in."""
from __future__ import annotations

from app.sports.base import SportAdapter
from app.sports.basketball import BasketballAdapter
from app.sports.cricket import CricketAdapter
from app.sports.football import FootballAdapter

ADAPTERS: dict[str, SportAdapter] = {a.key: a for a in (CricketAdapter(), FootballAdapter(), BasketballAdapter())}


class UnknownSport(KeyError):
    pass


def get_adapter(sport: str) -> SportAdapter:
    try:
        return ADAPTERS[sport]
    except KeyError as e:
        raise UnknownSport(sport) from e
