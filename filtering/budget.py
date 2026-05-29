"""Budget tier derivation from cost for two."""

from app.config import BUDGET_LOW_MAX, BUDGET_MEDIUM_MAX
from data.models import BudgetTier


def derive_budget_tier(
    cost_for_two: int | None,
    low_max: int = BUDGET_LOW_MAX,
    medium_max: int = BUDGET_MEDIUM_MAX,
) -> BudgetTier:
    """
    Map numeric cost to categorical budget tier.

    Rules (configurable via env):
      - low:    cost < low_max
      - medium: low_max <= cost < medium_max
      - high:   cost >= medium_max
    """
    if cost_for_two is None or cost_for_two <= 0:
        return BudgetTier.UNKNOWN

    if cost_for_two < low_max:
        return BudgetTier.LOW
    if cost_for_two < medium_max:
        return BudgetTier.MEDIUM
    return BudgetTier.HIGH
