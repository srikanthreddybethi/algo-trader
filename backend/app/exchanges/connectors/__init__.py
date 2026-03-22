"""Exchange connectors package — unified interface for non-ccxt brokers."""

from .base import BaseConnector
from .capital_connector import CapitalConnector
from .cmc_connector import CMCConnector
from .etoro_connector import EToroConnector
from .ibkr_connector import IBKRConnector
from .ig_connector import IGConnector
from .oanda_connector import OandaConnector
from .saxo_connector import SaxoConnector
from .trading212_connector import Trading212Connector

ALL_CONNECTORS: dict[str, type[BaseConnector]] = {
    "ig": IGConnector,
    "ibkr": IBKRConnector,
    "oanda": OandaConnector,
    "trading212": Trading212Connector,
    "etoro": EToroConnector,
    "saxo": SaxoConnector,
    "capital": CapitalConnector,
    "cmc": CMCConnector,
}

__all__ = [
    "BaseConnector",
    "IGConnector",
    "IBKRConnector",
    "OandaConnector",
    "Trading212Connector",
    "EToroConnector",
    "SaxoConnector",
    "CapitalConnector",
    "CMCConnector",
    "ALL_CONNECTORS",
]
