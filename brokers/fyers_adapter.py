"""
India Arbitrage Lab
Fyers broker adapter (API v3, SDK: pip install fyers-apiv3).

Credentials come from environment variables (never from code):
    FYERS_APP_ID        e.g. ABCD1234-100
    FYERS_ACCESS_TOKEN  the daily access token (it expires every day)

SAFETY
- IS_LIVE = True. Use it through GuardedBroker (create_broker("FYERS") does).
- Fail closed: an order is sent only if its contract_key is in symbol_map,
  e.g. {"NIFTY:FUTURES:2026-12-29": "NSE:NIFTY26DECFUT"}. Nothing is guessed.
- A Fyers order id means "accepted", not "filled", so filled=False is returned
  and the controller stops and tells you instead of assuming a fill.
- Written from Fyers v3 docs and tested only against a fake client here.
  Test once with a 1-quantity order before trusting it.
"""

import os
from typing import Any, Dict, List, Optional

from brokers.base import BrokerAdapter, BrokerError

SIDE = {"BUY": 1, "SELL": -1}
ORDER_TYPE = {"LIMIT": 1, "MARKET": 2}


def _client_from_env():
    app_id = os.environ.get("FYERS_APP_ID", "").strip()
    token = os.environ.get("FYERS_ACCESS_TOKEN", "").strip()
    if not app_id or not token:
        raise BrokerError(
            "Set FYERS_APP_ID and FYERS_ACCESS_TOKEN environment variables first."
        )
    try:
        from fyers_apiv3 import fyersModel
    except ImportError as exc:
        raise BrokerError("Install the SDK first: pip install fyers-apiv3") from exc
    return fyersModel.FyersModel(client_id=app_id, token=token, is_async=False, log_path="")


class FyersBroker(BrokerAdapter):
    NAME = "FYERS"
    IS_LIVE = True

    def __init__(
        self,
        client: Any = None,
        symbol_map: Optional[Dict[str, str]] = None,
        product_type: str = "INTRADAY",   # INTRADAY | MARGIN | CNC (choose per trade type)
    ):
        self.client = client if client is not None else _client_from_env()
        self.symbol_map = dict(symbol_map or {})
        self.product_type = product_type

    @staticmethod
    def _fail(reason: str) -> Dict[str, Any]:
        return {"success": False, "filled": False, "reason": reason}

    def submit_order(self, symbol, side, quantity, order_type="LIMIT", price=0.0) -> Dict[str, Any]:
        side = str(side).upper()
        order_type = str(order_type).upper()
        fyers_symbol = self.symbol_map.get(symbol)

        if fyers_symbol is None:
            return self._fail(f"No Fyers symbol mapped for {symbol}. Add it to symbol_map.")
        if side not in SIDE:
            return self._fail("Side must be BUY or SELL.")
        if order_type not in ORDER_TYPE:
            return self._fail("Order type must be LIMIT or MARKET.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            return self._fail("Quantity must be a positive integer.")
        if order_type == "LIMIT" and not float(price) > 0:
            return self._fail("Limit orders need a positive price.")

        payload = {
            "symbol": fyers_symbol,
            "qty": quantity,
            "type": ORDER_TYPE[order_type],
            "side": SIDE[side],
            "productType": self.product_type,
            "limitPrice": float(price) if order_type == "LIMIT" else 0,
            "stopPrice": 0,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": False,
        }
        try:
            response = self.client.place_order(data=payload)
        except Exception as exc:
            return self._fail(f"Fyers request failed: {type(exc).__name__}: {exc}")

        if not isinstance(response, dict) or response.get("s") != "ok" or not response.get("id"):
            message = response.get("message") if isinstance(response, dict) else response
            return self._fail(f"Fyers rejected the order: {message}")

        return {
            "success": True,
            "order_id": str(response["id"]),
            "filled": False,                 # accepted only; confirm in the order book
            "fill_price": float(price),
            "reason": "Order accepted by Fyers; fill not confirmed.",
        }

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        try:
            response = self.client.cancel_order(data={"id": order_id})
        except Exception as exc:
            return self._fail(f"Fyers request failed: {type(exc).__name__}: {exc}")
        ok = isinstance(response, dict) and response.get("s") == "ok"
        return {"success": ok, "reason": "" if ok else str(response)}

    def get_positions(self) -> List[Any]:
        response = self.client.positions()
        if not isinstance(response, dict) or response.get("s") != "ok":
            raise BrokerError(f"Could not read Fyers positions: {response}")
        return list(response.get("netPositions", []))

    def get_funds(self) -> Dict[str, float]:
        response = self.client.funds()
        if not isinstance(response, dict) or response.get("s") != "ok":
            raise BrokerError(f"Could not read Fyers funds: {response}")
        funds = {}
        for item in response.get("fund_limit", []):
            title = str(item.get("title", "")).strip()
            if title:
                funds[title] = float(item.get("equityAmount", 0.0) or 0.0)
        return funds
