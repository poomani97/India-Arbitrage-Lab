
import pytest

from strategies.strategy_registry import (
    StrategyRegistry,
    StrategyRegistryError,
)


def test_register_strategy():
    registry = StrategyRegistry()

    registry.register("S01", lambda data: data)

    assert registry.count() == 1
    assert registry.get("S01") is not None


def test_register_duplicate_strategy_fails():
    registry = StrategyRegistry()
    registry.register("S01", lambda data: data)

    with pytest.raises(StrategyRegistryError):
        registry.register("S01", lambda data: data)


def test_enable_disable_strategy():
    registry = StrategyRegistry()

    registry.register("S01", lambda data: data)

    registry.disable("S01")
    assert registry.is_enabled("S01") is False

    registry.enable("S01")
    assert registry.is_enabled("S01") is True


def test_enabled_and_disabled_names():
    registry = StrategyRegistry()

    registry.register("S01", lambda data: data)
    registry.register("S02", lambda data: data, enabled=False)

    assert registry.enabled_names() == ["S01"]
    assert registry.disabled_names() == ["S02"]


def test_unregister_strategy():
    registry = StrategyRegistry()

    registry.register("S01", lambda data: data)
    registry.unregister("S01")

    assert registry.count() == 0


def test_unknown_strategy_fails():
    registry = StrategyRegistry()

    with pytest.raises(StrategyRegistryError):
        registry.get("S99")


def test_none_strategy_rejected():
    registry = StrategyRegistry()

    with pytest.raises(StrategyRegistryError):
        registry.register("S01", None)


def test_registry_summary():
    registry = StrategyRegistry()

    registry.register("S01", lambda data: data)
    registry.register("S02", lambda data: data, enabled=False)

    result = registry.summary()

    assert result["total"] == 2
    assert result["enabled"] == 1
    assert result["disabled"] == 1
  
