r"""Income Projector — honest path from work income to capital-driven income.

Answers the owner question "when do earnings scale to \$100k/月?" with math, not
promises. The investment modules scale with capital, so this module compounds the
monthly savings that real work income produces and reports the intersection point
where portfolio income first exceeds (1) the work income and (2) a target monthly
income.

It never fabricates returns: the annual return rate is an explicit input with a
conservative default, and the projection is pure deterministic compounding.

Reuses no logic from other modules — this is a standalone financial simulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Conservative defaults (Zero Magic: all knobs named and documented).
DEFAULT_ANNUAL_RETURN = 0.10  # blended market return, honest not "50% optimized"
MAX_HORIZON_MONTHS = 1200  # cap the simulation at 100 years

_MONTHS_PER_YEAR = 12
_MONTHLY_RETURN_RATE = DEFAULT_ANNUAL_RETURN / _MONTHS_PER_YEAR


@dataclass(slots=True)
class IncomeProjection:
    """The time-to-income simulation result."""

    start_capital_usd: float
    savings_usd_per_month: float
    annual_return_rate: float
    target_monthly_usd: float
    months_to_target: int | None
    capital_at_target_usd: float
    crossing_months: int | None  # first month portfolio income >= work income
    portfolio_monthly_income_usd: float
    monthly_curve: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "start_capital_usd": round(self.start_capital_usd, 2),
            "savings_usd_per_month": round(self.savings_usd_per_month, 2),
            "annual_return_rate": round(self.annual_return_rate, 4),
            "target_monthly_usd": round(self.target_monthly_usd, 2),
            "months_to_target": self.months_to_target,
            "capital_at_target_usd": round(self.capital_at_target_usd, 2),
            "crossing_months": self.crossing_months,
            "portfolio_monthly_income_usd": round(self.portfolio_monthly_income_usd, 2),
            "crossing_after_work_income": bool(
                self.crossing_months is not None and self.portfolio_monthly_income_usd >= self.savings_usd_per_month
            ),
            "monthly_curve": self.monthly_curve,
        }


class IncomeProjector:
    """Deterministic compounding simulator: work income feeds capital overtime."""

    @staticmethod
    def project(
        work_income_usd_per_month: float,
        savings_usd_per_month: float,
        start_capital_usd: float = 0.0,
        annual_return_rate: float = DEFAULT_ANNUAL_RETURN,
        target_monthly_usd: float = 100_000.0,
        sample_every: int = 12,
    ) -> IncomeProjection:
        monthly_rate = annual_return_rate / _MONTHS_PER_YEAR
        capital = max(0.0, start_capital_usd)
        saved = max(0.0, savings_usd_per_month)
        target_month = None
        crossing_month = None
        capital_at_target = capital
        curve: list[dict] = []

        for month in range(1, MAX_HORIZON_MONTHS + 1):
            capital = capital * (1.0 + monthly_rate) + saved
            portfolio_income = capital * monthly_rate
            if (
                crossing_month is None
                and work_income_usd_per_month > 0
                and portfolio_income >= work_income_usd_per_month
            ):
                crossing_month = month
            if target_month is None and portfolio_income >= target_monthly_usd:
                target_month = month
                capital_at_target = capital
            if month % sample_every == 0 or month == 1:
                curve.append(
                    {
                        "month": month,
                        "capital_usd": round(capital, 2),
                        "portfolio_income_usd": round(portfolio_income, 2),
                    }
                )
        # if target never reached within horizon, use the final state
        final_capital = capital
        final_income = capital * monthly_rate
        return IncomeProjection(
            start_capital_usd=start_capital_usd,
            savings_usd_per_month=saved,
            annual_return_rate=annual_return_rate,
            target_monthly_usd=target_monthly_usd,
            months_to_target=target_month,
            capital_at_target_usd=capital_at_target if target_month else round(final_capital, 2),
            crossing_months=crossing_month,
            portfolio_monthly_income_usd=final_income,
            monthly_curve=curve,
        )


def project_income(
    work_income_usd_per_month: float,
    savings_usd_per_month: float,
    start_capital_usd: float = 0.0,
    annual_return_rate: float = DEFAULT_ANNUAL_RETURN,
    target_monthly_usd: float = 100_000.0,
) -> IncomeProjection:
    return IncomeProjector.project(
        work_income_usd_per_month=work_income_usd_per_month,
        savings_usd_per_month=savings_usd_per_month,
        start_capital_usd=start_capital_usd,
        annual_return_rate=annual_return_rate,
        target_monthly_usd=target_monthly_usd,
    )
