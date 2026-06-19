from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Optional
from football_agent.config.loader import load_bookmaker_profiles
from football_agent.schemas import OddsSnapshot


class BookmakerProfiler:
    def __init__(self, profiles: Optional[Dict] = None):
        self.profiles = profiles or load_bookmaker_profiles().get("bookmakers", {})

    def normalize_name(self, bookmaker: str) -> str:
        return bookmaker.lower().strip().replace(" ", "_").replace("-", "_")

    def profile(self, bookmaker: str) -> str:
        key = self.normalize_name(bookmaker)
        if key in self.profiles:
            return self.profiles[key].get("profile", "unknown")
        for k, v in self.profiles.items():
            label = self.normalize_name(v.get("label", ""))
            if key == label:
                return v.get("profile", "unknown")
        return "unknown"

    def enrich(self, odds: Iterable[OddsSnapshot]) -> List[OddsSnapshot]:
        out: List[OddsSnapshot] = []
        for o in odds:
            o.profile = self.profile(o.bookmaker)
            out.append(o)
        return out


def best_odds_by_selection(odds: Iterable[OddsSnapshot], prefer_profiles: Optional[List[str]] = None, allowed_markets: Optional[List[str]] = None) -> Dict[str, OddsSnapshot]:
    prefer_profiles = prefer_profiles or ["soft", "unknown", "semi-sharp", "sharp"]
    profile_rank = {p: i for i, p in enumerate(prefer_profiles)}
    best: Dict[str, OddsSnapshot] = {}
    for o in odds:
        if allowed_markets and o.market not in allowed_markets:
            continue
        current = best.get(o.selection)
        if current is None:
            best[o.selection] = o
            continue
        # Higher odds are better for the bettor. If equal, prefer desired profile order.
        if o.odds > current.odds or (o.odds == current.odds and profile_rank.get(o.profile, 9) < profile_rank.get(current.profile, 9)):
            best[o.selection] = o
    return best


def market_odds_matrix(odds: Iterable[OddsSnapshot], profile: Optional[str] = None, market: str = "1X2") -> Dict[str, float]:
    # Average odds per selection within a profile/market; useful for sharp baseline.
    buckets = defaultdict(list)
    for o in odds:
        if profile and o.profile != profile:
            continue
        if o.market == market and o.odds > 1:
            buckets[o.selection].append(o.odds)
    return {sel: sum(vals)/len(vals) for sel, vals in buckets.items() if vals}
