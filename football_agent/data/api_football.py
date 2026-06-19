from __future__ import annotations

import os
from datetime import date
from typing import Any, Dict, List, Optional
from .http import HttpClient
from football_agent.schemas import Competition, Fixture, OddsSnapshot


class ApiFootballClient:
    BASE_URL = "https://v3.football.api-sports.io"

    def __init__(self, api_key: Optional[str] = None, http: Optional[HttpClient] = None):
        self.api_key = api_key or os.getenv("API_FOOTBALL_KEY")
        self.http = http or HttpClient()
        self._disabled_reason: Optional[str] = None

    @property
    def enabled(self) -> bool:
        return bool(self.api_key) and self._disabled_reason is None

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise RuntimeError("API_FOOTBALL_KEY ontbreekt.")
        return {"x-apisports-key": self.api_key}

    def _get(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if self._disabled_reason:
            return {"response": [], "errors": {"disabled": self._disabled_reason}}
        data = self.http.get_json(f"{self.BASE_URL}/{endpoint.lstrip('/')}", headers=self._headers(), params=params)
        errors = data.get("errors")
        if isinstance(errors, dict) and errors.get("plan"):
            self._disabled_reason = str(errors.get("plan"))
        return data

    def fixtures(self, competition: Competition, season: int, date_from: date, date_to: date) -> List[Fixture]:
        if not competition.api_football_league_id:
            return []
        data = self._get("fixtures", {
            "league": competition.api_football_league_id,
            "season": season,
            "from": date_from.isoformat(),
            "to": date_to.isoformat(),
        })
        fixtures: List[Fixture] = []
        for item in data.get("response", []) or []:
            fixture = item.get("fixture", {}) or {}
            teams = item.get("teams", {}) or {}
            goals = item.get("goals", {}) or {}
            f_id = fixture.get("id")
            fixtures.append(
                Fixture(
                    id=f"af-{f_id}",
                    competition_key=competition.key,
                    competition_name=competition.name,
                    home_team=(teams.get("home") or {}).get("name", "Unknown home"),
                    away_team=(teams.get("away") or {}).get("name", "Unknown away"),
                    kickoff_utc=(fixture.get("date") or ""),
                    status=(fixture.get("status") or {}).get("long", "SCHEDULED"),
                    venue=(fixture.get("venue") or {}).get("name"),
                    city=(fixture.get("venue") or {}).get("city"),
                    home_score=goals.get("home"),
                    away_score=goals.get("away"),
                    source="api-football",
                    api_football_fixture_id=f_id,
                )
            )
        return fixtures

    def odds(self, fixture_id: int, bookmaker_ids: Optional[List[int]] = None) -> List[OddsSnapshot]:
        params: Dict[str, Any] = {"fixture": fixture_id}
        data = self._get("odds", params)
        snapshots: List[OddsSnapshot] = []
        for resp in data.get("response", []) or []:
            update = resp.get("update") or ""
            for bookmaker in resp.get("bookmakers", []) or []:
                b_name = str(bookmaker.get("name", "unknown")).lower().replace(" ", "_")
                for bet in bookmaker.get("bets", []) or []:
                    bet_name = str(bet.get("name", "")).lower()
                    for val in bet.get("values", []) or []:
                        label = str(val.get("value", "")).lower()
                        market = None
                        selection = None
                        if bet_name in {"match winner", "1x2"}:
                            market = "1X2"
                            selection = "DRAW" if label in {"draw", "x"} else "HOME" if label in {"home", "1"} else "AWAY" if label in {"away", "2"} else None
                        elif "over/under" in bet_name or "goals over/under" in bet_name or bet_name in {"goals over/under"}:
                            # API-Football commonly labels values as "Over 2.5" / "Under 2.5".
                            if "2.5" in label and "over" in label:
                                market = "OVER_UNDER_2_5"
                                selection = "OVER_2_5"
                            elif "2.5" in label and "under" in label:
                                market = "OVER_UNDER_2_5"
                                selection = "UNDER_2_5"
                        elif "both teams" in bet_name or "both teams score" in bet_name:
                            market = "BTTS"
                            if label in {"yes", "y"}:
                                selection = "BTTS_YES"
                            elif label in {"no", "n"}:
                                selection = "BTTS_NO"
                        if not market or not selection:
                            continue
                        try:
                            odd = float(val.get("odd"))
                        except (TypeError, ValueError):
                            continue
                        snapshots.append(OddsSnapshot(bookmaker=b_name, market=market, selection=selection, odds=odd, timestamp_utc=update))
        return snapshots

    def injuries(self, fixture_id: int) -> List[Dict[str, Any]]:
        data = self._get("injuries", {"fixture": fixture_id})
        return list(data.get("response", []) or [])

    def lineups(self, fixture_id: int) -> List[Dict[str, Any]]:
        data = self._get("fixtures/lineups", {"fixture": fixture_id})
        return list(data.get("response", []) or [])
