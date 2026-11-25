
"""
India Arbitrage Lab
STEP 21 - Strategy Registry

Central registry for S01-S10 strategy modules.
This registry does not generate trading signals by itself.
"""

from typing import Any, Dict, List


class StrategyRegistryError(Exception):
    """Strategy registration or execution error."""


class StrategyRegistry:
    def __init__(self):
        self._strategies: Dict[str, Any] = {}
        self._enabled: Dict[str, bool] = {}

    def register(self, name: str, strategy: Any, enabled: bool = True):
        name = str(name).strip().upper()

        if not name:
            raise StrategyRegistryError(
                "Strategy name cannot be empty."
            )

        if strategy is None:
            raise StrategyRegistryError(
                f"Strategy {name} cannot be None."
            )

        if name in self._strategies:
            raise StrategyRegistryError(
                f"Strategy {name} is already registered."
            )

        self._strategies[name] = strategy
        self._enabled[name] = bool(enabled)

        return name

    def unregister(self, name: str):
        name = name.upper()

        if name not in self._strategies:
            raise StrategyRegistryError(
                f"Strategy {name} is not registered."
            )

        del self._strategies[name]
        del self._enabled[name]

    def get(self, name: str):
        name = name.upper()

        if name not in self._strategies:
            raise StrategyRegistryError(
                f"Strategy {name} not found."
            )

        return self._strategies[name]

    def enable(self, name: str):
        name = name.upper()
        self.get(name)
        self._enabled[name] = True

    def disable(self, name: str):
        name = name.upper()
        self.get(name)
        self._enabled[name] = False

    def is_enabled(self, name: str) -> bool:
        name = name.upper()
        self.get(name)
        return self._enabled[name]

    def all_names(self) -> List[str]:
        return list(self._strategies.keys())

    def enabled_names(self) -> List[str]:
        return [
            name
            for name in self._strategies
            if self._enabled[name]
        ]

    def disabled_names(self) -> List[str]:
        return [
            name
            for name in self._strategies
            if not self._enabled[name]
        ]

    def count(self) -> int:
        return len(self._strategies)

    def summary(self) -> Dict[str, Any]:
        return {
            "total": self.count(),
            "enabled": len(self.enabled_names()),
            "disabled": len(self.disabled_names()),
            "strategies": {
                name: {
                    "enabled": self._enabled[name],
                    "type": type(self._strategies[name]).__name__,
                }
                for name in self._strategies
            },
        }
      
