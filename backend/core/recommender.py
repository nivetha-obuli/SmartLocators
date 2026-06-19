from typing import List
from backend.models.schemas import Locator, ReliabilityScore


class LocatorRecommender:
    """
    Scores and ranks locators. Applies bonus/penalty rules
    based on automation best-practices.
    """

    STRATEGY_WEIGHTS = {
        "test-id-based":   1.00,
        "id-based":        0.95,
        "aria-based":      0.90,
        "name-based":      0.88,
        "placeholder-based": 0.75,
        "attribute-based": 0.73,
        "class-based":     0.65,
        "exact-text":      0.70,
        "partial-text":    0.60,
        "type-value":      0.68,
        "type-based":      0.45,
        "nth-child":       0.40,
        "absolute-xpath":  0.25,
    }

    def rank(self, locators: List[Locator]) -> List[Locator]:
        for loc in locators:
            base = self.STRATEGY_WEIGHTS.get(loc.strategy, loc.score)
            bonus = self._compute_bonus(loc)
            penalty = self._compute_penalty(loc)
            final = min(max(base + bonus - penalty, 0.0), 1.0)
            loc.score = round(final, 3)
            loc.reliability = self._score_to_reliability(final)

        return sorted(locators, key=lambda x: x.score, reverse=True)

    def pick_best(self, locators: List[Locator]) -> Locator:
        ranked = self.rank(locators)
        return ranked[0] if ranked else locators[0]

    def _compute_bonus(self, loc: Locator) -> float:
        bonus = 0.0
        if "data-testid" in loc.value or "data-cy" in loc.value:
            bonus += 0.05
        if "aria-label" in loc.value:
            bonus += 0.03
        # Short, clean selectors are preferred
        if len(loc.value) < 40:
            bonus += 0.02
        return bonus

    def _compute_penalty(self, loc: Locator) -> float:
        penalty = 0.0
        # Long absolute xpaths
        if loc.value.count("/") > 6:
            penalty += 0.15
        # Dynamic-looking values
        import re
        if re.search(r'\d{4,}', loc.value):
            penalty += 0.10
        if len(loc.value) > 120:
            penalty += 0.08
        return penalty

    def _score_to_reliability(self, score: float) -> ReliabilityScore:
        if score >= 0.80:
            return ReliabilityScore.HIGH
        elif score >= 0.55:
            return ReliabilityScore.MEDIUM
        return ReliabilityScore.LOW