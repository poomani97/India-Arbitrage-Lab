
from dataclasses import dataclass, asdict
from math import exp, isfinite


@dataclass
class FairValueResult:
    spot_price: float
    fair_value: float
    actual_futures_price: float
    theoretical_basis: float
    actual_basis: float
    mispricing: float
    time_to_expiry_years: float
    annual_interest_rate: float
    annual_dividend_yield: float
    method: str

    def to_dict(self):
        return asdict(self)


class FairValueCalculator:
    """
    Theoretical futures fair-value calculator.

    Rates must be supplied as decimal fractions:
        0.07 = 7%
        0.02 = 2%

    Methods:
        continuous: exp((r - q) * T)
        simple:     1 + (r - q) * T

    This calculator is for research. It does not account for every
    contract-specific feature, tax, financing convention or settlement rule.
    """

    @staticmethod
    def _validate_number(name: str, value: float):
        if not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be numeric")

        if not isfinite(value):
            raise ValueError(f"{name} must be finite")

    def calculate(
        self,
        spot_price: float,
        days_to_expiry: int,
        annual_interest_rate: float = 0.0,
        annual_dividend_yield: float = 0.0,
        actual_futures_price: float = 0.0,
        method: str = "continuous",
        days_per_year: int = 365,
    ) -> FairValueResult:

        self._validate_number("spot_price", spot_price)
        self._validate_number("annual_interest_rate", annual_interest_rate)
        self._validate_number(
            "annual_dividend_yield",
            annual_dividend_yield,
        )
        self._validate_number(
            "actual_futures_price",
            actual_futures_price,
        )

        if spot_price <= 0:
            raise ValueError("spot_price must be greater than zero")

        if days_to_expiry < 0:
            raise ValueError("days_to_expiry cannot be negative")

        if days_per_year <= 0:
            raise ValueError("days_per_year must be positive")

        if actual_futures_price < 0:
            raise ValueError("actual_futures_price cannot be negative")

        if method not in ("continuous", "simple"):
            raise ValueError(
                "method must be 'continuous' or 'simple'"
            )

        time_years = days_to_expiry / days_per_year

        net_rate = (
            annual_interest_rate
            - annual_dividend_yield
        )

        if method == "continuous":
            fair_value = spot_price * exp(net_rate * time_years)

        else:
            factor = 1 + net_rate * time_years

            if factor < 0:
                raise ValueError(
                    "Simple-compounding factor cannot be negative"
                )

            fair_value = spot_price * factor

        theoretical_basis = fair_value - spot_price

        actual_basis = (
            actual_futures_price - spot_price
            if actual_futures_price > 0
            else 0.0
        )

        mispricing = (
            actual_futures_price - fair_value
            if actual_futures_price > 0
            else 0.0
        )

        return FairValueResult(
            spot_price=round(spot_price, 4),
            fair_value=round(fair_value, 4),
            actual_futures_price=round(
                actual_futures_price, 4
            ),
            theoretical_basis=round(theoretical_basis, 4),
            actual_basis=round(actual_basis, 4),
            mispricing=round(mispricing, 4),
            time_to_expiry_years=round(time_years, 8),
            annual_interest_rate=annual_interest_rate,
            annual_dividend_yield=annual_dividend_yield,
            method=method,
        )
      
