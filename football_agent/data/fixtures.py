from __future__ import annotations

from datetime import date, timedelta
from typing import List
from football_agent.config.loader import load_competitions
from football_agent.schemas import Competition, Fixture
from .football_data import FootballDataClient
from .api_football import ApiFootballClient


class FixtureProvider:
    def __init__(self, football_data: FootballDataClient | None = None, api_football: ApiFootballClient | None = None):
        self.football_data = football_data or FootballDataClient()
        self.api_football = api_football or ApiFootballClient()

    def competitions(self) -> List[Competition]:
        raw = load_competitions()
        return [Competition(**c) for c in raw.get("competitions", [])]

    def upcoming(self, days_ahead: int = 7, max_matches: int = 80) -> List[Fixture]:
        today = date.today()
        date_to = today + timedelta(days=days_ahead)
        season = int(load_competitions().get("season", today.year))
        fixtures: List[Fixture] = []
        for comp in self.competitions():
            got: List[Fixture] = []
            if self.football_data.enabled and comp.football_data_code:
                try:
                    got = self.football_data.matches(comp, today, date_to)
                except Exception as exc:
                    print(f"football-data faalde voor {comp.name}: {exc}")
            if not got and self.api_football.enabled and comp.api_football_league_id:
                try:
                    got = self.api_football.fixtures(comp, season, today, date_to)
                except Exception as exc:
                    print(f"api-football faalde voor {comp.name}: {exc}")
            fixtures.extend(got)
        fixtures.sort(key=lambda f: f.kickoff_utc)
        # de-duplicate on matchup+kickoff+competition
        seen = set()
        unique: List[Fixture] = []
        for f in fixtures:
            key = (f.competition_key, f.home_team.lower(), f.away_team.lower(), f.kickoff_utc[:10])
            if key in seen:
                continue
            seen.add(key)
            unique.append(f)
        return unique[:max_matches]
