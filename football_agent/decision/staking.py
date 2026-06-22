from __future__ import annotations

from dataclasses import dataclass
from football_agent.utils import clamp


@dataclass
class StakeRecommendation:
    raw_kelly_fraction: float
    fractional_kelly: float
    stake_units: float
    reason: str


class FractionalKellyStaking:
    """Defensive fractional Kelly stake model for premium Telegram picks.

    The output is a unit-size risk indication, never a euro amount. It combines
    Kelly with strict bankroll protection: one blended risk multiplier,
    dynamic caps and a minimum-display threshold. This avoids aggressive 4-5 unit
    recommendations before the model has a large verified live sample.
    """

    def __init__(
        self,
        kelly_fraction: float = 0.15,
        bankroll_units: float = 100.0,
        max_units_per_pick: float = 2.0,
        min_units_for_value: float = 0.25,
    ):
        self.kelly_fraction = clamp(kelly_fraction, 0.0, 1.0)
        self.bankroll_units = max(1.0, bankroll_units)
        self.max_units_per_pick = max(0.0, max_units_per_pick)
        self.min_units_for_value = max(0.0, min_units_for_value)

    @staticmethod
    def _dynamic_cap(data_quality: float, confidence: float, uncertainty_score: float, configured_cap: float) -> float:
        # Strong but not reckless. Only exceptional, low-uncertainty picks may reach 2 units.
        if data_quality >= 9.0 and confidence >= 9.0 and uncertainty_score <= 2.5:
            cap = 2.0
        elif data_quality >= 8.3 and confidence >= 8.2 and uncertainty_score <= 4.0:
            cap = 1.5
        elif data_quality >= 7.5 and confidence >= 7.5 and uncertainty_score <= 5.5:
            cap = 1.0
        else:
            cap = 0.5
        return min(configured_cap, cap)

    @staticmethod
    def _round_units(units: float) -> float:
        # Keep member-facing units simple and conservative: 0.25 unit increments, rounded down.
        return max(0.0, int(units * 4.0) / 4.0)

    def recommend(
        self,
        *,
        model_probability: float,
        decimal_odds: float | None,
        uncertainty_score: float,
        data_quality: float,
        confidence: float,
    ) -> StakeRecommendation:
        if decimal_odds is None or decimal_odds <= 1.0 or model_probability <= 0.0:
            return StakeRecommendation(0.0, 0.0, 0.0, "Geen geldige odds/modelkans voor Kelly.")
        if data_quality < 7.0 or confidence < 7.0 or uncertainty_score > 6.5:
            return StakeRecommendation(0.0, 0.0, 0.0, "Geen stake: data/confidence/uncertainty voldoet niet aan premium guardrails.")

        b = decimal_odds - 1.0
        p = clamp(model_probability, 0.0, 1.0)
        q = 1.0 - p
        raw = (b * p - q) / b if b > 0 else 0.0
        raw = max(0.0, raw)
        # V25.0.9: NoBetRules already blocks weak/high-uncertainty picks.
        # After a pick passes those guardrails, avoid triple-discounting the stake.
        # Use one blended risk multiplier instead: still defensive, but it preserves
        # meaningful separation between a normal pick and a genuinely strong pick.
        uncertainty_component = clamp(1.0 - (uncertainty_score / 10.0), 0.20, 1.0)
        quality_component = clamp(((data_quality + confidence) / 20.0), 0.50, 1.0)
        risk_multiplier = clamp((0.65 * uncertainty_component) + (0.35 * quality_component), 0.25, 1.0)
        fractional = raw * self.kelly_fraction * risk_multiplier
        dynamic_cap = self._dynamic_cap(data_quality, confidence, uncertainty_score, self.max_units_per_pick)
        units = clamp(fractional * self.bankroll_units, 0.0, dynamic_cap)
        units = self._round_units(units)
        if 0.0 < units < self.min_units_for_value:
            units = 0.0
            reason = (
                f"Kelly raw {raw:.2%}; fractie {self.kelly_fraction:.2f}; uitkomst onder minimum "
                f"{self.min_units_for_value:.2f}u, dus geen officiële stake."
            )
            return StakeRecommendation(raw, fractional, units, reason)
        reason = (
            f"Kelly raw {raw:.2%}; fractie {self.kelly_fraction:.2f}; één risk multiplier toegepast; "
            f"dynamische cap {dynamic_cap:.2f}u; units afgerond naar {units:.2f}u."
        )
        return StakeRecommendation(raw, fractional, units, reason)
