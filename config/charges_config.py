from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ChargeRates:
    """
    Configurable Indian market trading charges.

    Rates must be verified against official exchange/broker sources
    before being used for real trading calculations.

    Percentage rates are expressed as percentages:
    0.05 means 0.05%, NOT 5%.
    """

    # Brokerage charged by broker (% of turnover)
    brokerage_percent: float = 0.0

    # Securities Transaction Tax (%)
    stt_percent: float = 0.0

    # Exchange transaction charge (%)
    exchange_transaction_percent: float = 0.0

    # SEBI turnover fee (%)
    sebi_fee_percent: float = 0.0

    # GST (%)
    gst_percent: float = 0.0

    # Stamp duty (%)
    stamp_duty_percent: float = 0.0

    # Additional estimated cost per order (₹)
    miscellaneous_per_order: float = 0.0

    # Slippage estimate (%)
    slippage_percent: float = 0.0

    # Whether the rates have been checked against official sources
    verified: bool = False

    # Verification details
    verification_source: Optional[str] = None
    effective_from: Optional[str] = None

    def validate(self):
        """Validate charge configuration."""

        percentage_fields = [
            self.brokerage_percent,
            self.stt_percent,
            self.exchange_transaction_percent,
            self.sebi_fee_percent,
            self.gst_percent,
            self.stamp_duty_percent,
            self.slippage_percent,
        ]

        for rate in percentage_fields:
            if rate < 0:
                raise ValueError("Charge rates cannot be negative")

        if self.miscellaneous_per_order < 0:
            raise ValueError(
                "Miscellaneous charges cannot be negative"
            )

        if self.verified and not self.verification_source:
            raise ValueError(
                "Verified rates must include a verification source"
            )

        if self.verified and not self.effective_from:
            raise ValueError(
                "Verified rates must include an effective date"
            )

        return True


@dataclass
class ChargesConfig:
    """
    Holds charge configurations for different instrument categories.

    Rates are intentionally set to zero until verified and configured.
    These defaults must not be interpreted as actual market charges.
    """

    # Instrument-specific rate profiles
    profiles: Dict[str, ChargeRates] = field(default_factory=dict)

    # Global configuration
    currency: str = "INR"
    require_verified_rates: bool = True

    def add_profile(
        self,
        instrument_type: str,
        rates: ChargeRates,
    ):
        """Add or replace a charge profile."""

        if not instrument_type:
            raise ValueError("instrument_type cannot be empty")

        rates.validate()

        self.profiles[instrument_type.upper()] = rates

    def get_profile(self, instrument_type: str):
        """Get a charge profile by instrument type."""

        key = instrument_type.upper()

        if key not in self.profiles:
            raise KeyError(
                f"Charge profile not configured: {instrument_type}"
            )

        profile = self.profiles[key]

        if self.require_verified_rates and not profile.verified:
            raise ValueError(
                f"Charge profile {key} is not verified. "
                "Research calculations using actual charges are blocked."
            )

        return profile

    def is_configured(self, instrument_type: str) -> bool:
        """Check whether an instrument profile exists."""

        return instrument_type.upper() in self.profiles

    def list_profiles(self):
        """Return configured instrument profile names."""

        return list(self.profiles.keys())


def create_default_charges_config():
    """
    Create initial charge configuration.

    Rates are zero and unverified intentionally.
    Official rates will be researched and added later.
    """

    config = ChargesConfig()

    # Cash equity delivery
    config.add_profile(
        "EQUITY_DELIVERY",
        ChargeRates(),
    )

    # Equity intraday
    config.add_profile(
        "EQUITY_INTRADAY",
        ChargeRates(),
    )

    # Equity futures
    config.add_profile(
        "FUTURES",
        ChargeRates(),
    )

    # Equity options
    config.add_profile(
        "OPTIONS",
        ChargeRates(),
    )

    # ETF transactions
    config.add_profile(
        "ETF",
        ChargeRates(),
    )

    # Index-related research
    config.add_profile(
        "INDEX",
        ChargeRates(),
    )

    return config
  
