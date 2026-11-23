
from dataclasses import dataclass, asdict
from math import isfinite

from config.charges_config import ChargesConfig, ChargeRates


@dataclass
class ChargeBreakdown:
    instrument_type: str
    buy_turnover: float
    sell_turnover: float
    total_turnover: float

    brokerage: float
    stt: float
    exchange_transaction_charge: float
    sebi_fee: float
    gst: float
    stamp_duty: float
    miscellaneous: float
    estimated_slippage: float

    total_charges: float
    net_turnover_cost_percent: float
    verified_rates: bool

    def to_dict(self):
        return asdict(self)


class ChargesCalculator:
    """
    Estimated transaction charge calculator.

    Rates are percentage values:
        0.10 means 0.10%, not 10%.

    This is a configurable research calculator.
    Exact exchange, broker and instrument-specific charge
    treatment must be verified before relying on its output.
    """

    def __init__(self, config: ChargesConfig):
        self.config = config

    @staticmethod
    def _validate_number(name: str, value: float):
        if not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be numeric")

        if not isfinite(value):
            raise ValueError(f"{name} must be finite")

        if value < 0:
            raise ValueError(f"{name} cannot be negative")

    @staticmethod
    def _percentage_amount(turnover: float, rate_percent: float):
        """Convert percentage rate into rupee amount."""

        return turnover * rate_percent / 100.0

    def calculate(
        self,
        instrument_type: str,
        buy_turnover: float,
        sell_turnover: float,
        order_count: int = 2,
    ) -> ChargeBreakdown:

        self._validate_number("buy_turnover", buy_turnover)
        self._validate_number("sell_turnover", sell_turnover)

        if not isinstance(order_count, int) or order_count < 0:
            raise ValueError("order_count must be a non-negative integer")

        # Fetch the configured instrument profile.
        # Unverified profiles are blocked by config settings.
        rates: ChargeRates = self.config.get_profile(instrument_type)

        total_turnover = buy_turnover + sell_turnover

        # Brokerage: estimated on total traded turnover.
        brokerage = self._percentage_amount(
            total_turnover,
            rates.brokerage_percent,
        )

        # STT: simplified percentage calculation.
        # Actual applicability/rate depends on instrument and transaction.
        stt = self._percentage_amount(
            total_turnover,
            rates.stt_percent,
        )

        # Exchange transaction charge.
        exchange_charge = self._percentage_amount(
            total_turnover,
            rates.exchange_transaction_percent,
        )

        # SEBI turnover fee.
        sebi_fee = self._percentage_amount(
            total_turnover,
            rates.sebi_fee_percent,
        )

        # GST: applied to the configured taxable components here.
        # Exact treatment should be verified for the broker/instrument.
        taxable_components = (
            brokerage
            + exchange_charge
            + sebi_fee
        )

        gst = self._percentage_amount(
            taxable_components,
            rates.gst_percent,
        )

        # Stamp duty: simplified buy-side calculation.
        stamp_duty = self._percentage_amount(
            buy_turnover,
            rates.stamp_duty_percent,
        )

        # Additional configured charge per order.
        miscellaneous = (
            rates.miscellaneous_per_order * order_count
        )

        # Estimated slippage on total turnover.
        estimated_slippage = self._percentage_amount(
            total_turnover,
            rates.slippage_percent,
        )

        total_charges = (
            brokerage
            + stt
            + exchange_charge
            + sebi_fee
            + gst
            + stamp_duty
            + miscellaneous
            + estimated_slippage
        )

        if total_turnover > 0:
            cost_percent = (
                total_charges / total_turnover
            ) * 100.0
        else:
            cost_percent = 0.0

        return ChargeBreakdown(
            instrument_type=instrument_type.upper(),
            buy_turnover=buy_turnover,
            sell_turnover=sell_turnover,
            total_turnover=total_turnover,
            brokerage=round(brokerage, 4),
            stt=round(stt, 4),
            exchange_transaction_charge=round(exchange_charge, 4),
            sebi_fee=round(sebi_fee, 4),
            gst=round(gst, 4),
            stamp_duty=round(stamp_duty, 4),
            miscellaneous=round(miscellaneous, 4),
            estimated_slippage=round(estimated_slippage, 4),
            total_charges=round(total_charges, 4),
            net_turnover_cost_percent=round(cost_percent, 6),
            verified_rates=rates.verified,
        )
      
