
# India Arbitrage Lab
# Base Strategy Framework
# Common foundation for all arbitrage strategies

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import pandas as pd

from models.opportunity import Opportunity
from contracts.contract_master import ContractMaster


class BaseStrategy(ABC):
    """Abstract base class for all research strategies."""

    STRATEGY_ID = "BASE"
    STRATEGY_NAME = "Base Strategy"
    STRATEGY_DESCRIPTION = "Abstract strategy template"
    STRATEGY_VERSION = "1.0.0"

    def __init__(
        self,
        enabled: bool = True,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.enabled = enabled
        self.config = config.copy() if config else {}
        self.validate_config()

    @abstractmethod
    def scan(
        self,
        data: pd.DataFrame,
        contract_master: Optional[ContractMaster] = None,
    ) -> List[Opportunity]:
        """Analyze market data and return detected opportunities."""
        raise NotImplementedError

    def validate_config(self) -> None:
        """Validate the strategy's configuration."""
        if not isinstance(self.config, dict):
            raise TypeError("Strategy config must be a dictionary")

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the strategy."""
        if not isinstance(enabled, bool):
            raise TypeError("enabled must be a boolean")
        self.enabled = enabled

    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update strategy configuration."""
        if not isinstance(updates, dict):
            raise TypeError("Config updates must be a dictionary")

        self.config.update(updates)
        self.validate_config()

    def get_config(self) -> Dict[str, Any]:
        """Return a copy of the strategy configuration."""
        return self.config.copy()

    def get_metadata(self) -> Dict[str, Any]:
        """Return strategy identification and runtime information."""
        return {
            "strategy_id": self.STRATEGY_ID,
            "strategy_name": self.STRATEGY_NAME,
            "description": self.STRATEGY_DESCRIPTION,
            "version": self.STRATEGY_VERSION,
            "enabled": self.enabled,
            "config": self.get_config(),
        }

    def check_data(self, data: pd.DataFrame) -> bool:
        """Perform basic data checks before strategy analysis."""
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Strategy input must be a pandas DataFrame")

        if data.empty:
            return False

        required_columns = {"datetime", "open", "high", "low", "close"}
        return required_columns.issubset(data.columns)

    def safe_scan(
        self,
        data: pd.DataFrame,
        contract_master: Optional[ContractMaster] = None,
    ) -> List[Opportunity]:
        """Run a scan only when enabled and data is usable."""

        if not self.enabled:
            return []

        if not self.check_data(data):
            return []

        results = self.scan(
            data=data,
            contract_master=contract_master,
        )

        if results is None:
            return []

        if not isinstance(results, list):
            raise TypeError("Strategy scan must return a list")

        for item in results:
            if not isinstance(item, Opportunity):
                raise TypeError(
                    "Strategy results must contain Opportunity objects"
                )

        return results
      
