"""
Placeholders for real brokers. Each one raises NotImplementedError until its
API is wired in (needs your API keys and a small test with tiny quantity).
Put keys in environment variables or a git-ignored .env file, never in code.
"""

from brokers.base import NotConnectedBroker


class DhanBroker(NotConnectedBroker):
    NAME = "DHAN"
    API_NOTES = "Needs Dhan client id and access token."


class AngelOneBroker(NotConnectedBroker):
    NAME = "ANGELONE"
    API_NOTES = "Needs Angel One SmartAPI key, client code and TOTP."


class GrowwBroker(NotConnectedBroker):
    NAME = "GROWW"
    API_NOTES = "Check first whether Groww offers a trading API for your account."


class ForexBroker(NotConnectedBroker):
    NAME = "FOREX"
    API_NOTES = ("Forex needs its own lot/pip/leverage cost model. Offshore forex "
                 "may not be permitted for Indian residents; confirm with your broker.")
