from __future__ import annotations


class TradingError(Exception):
    """Base exception for all trading-related errors."""


class ConfigurationError(TradingError):
    """Invalid or missing trading configuration."""


class InsufficientBalanceError(TradingError):
    """Not enough balance to execute the order."""


class OrderRejectedError(TradingError):
    """Order was rejected by the exchange or simulator."""


class OrderNotFoundError(TradingError):
    """Order ID does not exist."""


class InvalidOrderStateError(TradingError):
    """Operation not valid for the current order state."""


class UnsupportedExchangeError(TradingError):
    """Exchange or DEX is not supported."""


class WalletPersistenceError(TradingError):
    """Failed to save or load virtual wallet state."""


class SecurityViolationError(TradingError):
    """Attempted to sign or broadcast a real transaction in simulation mode."""
