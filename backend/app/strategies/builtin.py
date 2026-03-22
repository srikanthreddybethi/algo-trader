"""Pre-built trading strategies."""
import numpy as np
import pandas as pd
from typing import List, Dict
from app.strategies.base import BaseStrategy, StrategyParam
from app.strategies.pure_ai import PureAI_Strategy


class SMA_Crossover(BaseStrategy):
    name = "SMA Crossover"
    description = "Buy when short SMA crosses above long SMA, sell when it crosses below."
    category = "trend"

    @classmethod
    def get_params(cls) -> List[StrategyParam]:
        return [
            StrategyParam("short_window", "Short SMA Period", "int", 20, min=5, max=100, step=1),
            StrategyParam("long_window", "Long SMA Period", "int", 50, min=10, max=300, step=1),
        ]

    def generate_signals(self, df: pd.DataFrame, params: Dict) -> pd.DataFrame:
        short = params.get("short_window", 20)
        long_ = params.get("long_window", 50)
        df = df.copy()
        df["sma_short"] = df["close"].rolling(window=short).mean()
        df["sma_long"] = df["close"].rolling(window=long_).mean()
        df["signal"] = 0
        df.loc[df["sma_short"] > df["sma_long"], "signal"] = 1
        df.loc[df["sma_short"] <= df["sma_long"], "signal"] = -1
        # Only trigger on crossover points
        df["signal"] = df["signal"].diff().div(2).fillna(0).astype(int)
        return df


class EMA_Crossover(BaseStrategy):
    name = "EMA Crossover"
    description = "Buy when short EMA crosses above long EMA, sell when it crosses below. Faster response than SMA."
    category = "trend"

    @classmethod
    def get_params(cls) -> List[StrategyParam]:
        return [
            StrategyParam("short_window", "Short EMA Period", "int", 12, min=3, max=100, step=1),
            StrategyParam("long_window", "Long EMA Period", "int", 26, min=5, max=300, step=1),
        ]

    def generate_signals(self, df: pd.DataFrame, params: Dict) -> pd.DataFrame:
        short = params.get("short_window", 12)
        long_ = params.get("long_window", 26)
        df = df.copy()
        df["ema_short"] = df["close"].ewm(span=short, adjust=False).mean()
        df["ema_long"] = df["close"].ewm(span=long_, adjust=False).mean()
        df["signal"] = 0
        df.loc[df["ema_short"] > df["ema_long"], "signal"] = 1
        df.loc[df["ema_short"] <= df["ema_long"], "signal"] = -1
        df["signal"] = df["signal"].diff().div(2).fillna(0).astype(int)
        return df


class RSI_Strategy(BaseStrategy):
    name = "RSI"
    description = "Buy when RSI drops below oversold threshold, sell when it rises above overbought."
    category = "mean_reversion"

    @classmethod
    def get_params(cls) -> List[StrategyParam]:
        return [
            StrategyParam("period", "RSI Period", "int", 14, min=5, max=50, step=1),
            StrategyParam("oversold", "Oversold Threshold", "int", 30, min=10, max=45, step=1),
            StrategyParam("overbought", "Overbought Threshold", "int", 70, min=55, max=90, step=1),
        ]

    def generate_signals(self, df: pd.DataFrame, params: Dict) -> pd.DataFrame:
        period = params.get("period", 14)
        oversold = params.get("oversold", 30)
        overbought = params.get("overbought", 70)
        df = df.copy()
        delta = df["close"].diff()
        gain = delta.clip(lower=0).rolling(window=period).mean()
        loss = (-delta.clip(upper=0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))
        df["signal"] = 0
        df.loc[df["rsi"] < oversold, "signal"] = 1
        df.loc[df["rsi"] > overbought, "signal"] = -1
        # Only trigger on threshold crossings
        prev_signal = df["signal"].shift(1).fillna(0)
        df["signal"] = np.where(df["signal"] != prev_signal, df["signal"], 0)
        return df


class MACD_Strategy(BaseStrategy):
    name = "MACD"
    description = "Buy on MACD bullish crossover (MACD crosses above signal line), sell on bearish crossover."
    category = "trend"

    @classmethod
    def get_params(cls) -> List[StrategyParam]:
        return [
            StrategyParam("fast_period", "Fast EMA Period", "int", 12, min=5, max=50, step=1),
            StrategyParam("slow_period", "Slow EMA Period", "int", 26, min=10, max=100, step=1),
            StrategyParam("signal_period", "Signal Period", "int", 9, min=3, max=30, step=1),
        ]

    def generate_signals(self, df: pd.DataFrame, params: Dict) -> pd.DataFrame:
        fast = params.get("fast_period", 12)
        slow = params.get("slow_period", 26)
        sig_period = params.get("signal_period", 9)
        df = df.copy()
        df["ema_fast"] = df["close"].ewm(span=fast, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=slow, adjust=False).mean()
        df["macd"] = df["ema_fast"] - df["ema_slow"]
        df["macd_signal"] = df["macd"].ewm(span=sig_period, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]
        df["signal"] = 0
        df.loc[df["macd"] > df["macd_signal"], "signal"] = 1
        df.loc[df["macd"] <= df["macd_signal"], "signal"] = -1
        df["signal"] = df["signal"].diff().div(2).fillna(0).astype(int)
        return df


class BollingerBands_Strategy(BaseStrategy):
    name = "Bollinger Bands"
    description = "Buy when price touches lower band (oversold), sell when it touches upper band (overbought)."
    category = "mean_reversion"

    @classmethod
    def get_params(cls) -> List[StrategyParam]:
        return [
            StrategyParam("period", "BB Period", "int", 20, min=10, max=100, step=1),
            StrategyParam("std_dev", "Standard Deviations", "float", 2.0, min=1.0, max=3.5, step=0.1),
        ]

    def generate_signals(self, df: pd.DataFrame, params: Dict) -> pd.DataFrame:
        period = params.get("period", 20)
        std_dev = params.get("std_dev", 2.0)
        df = df.copy()
        df["bb_mid"] = df["close"].rolling(window=period).mean()
        rolling_std = df["close"].rolling(window=period).std()
        df["bb_upper"] = df["bb_mid"] + (rolling_std * std_dev)
        df["bb_lower"] = df["bb_mid"] - (rolling_std * std_dev)
        df["signal"] = 0
        df.loc[df["close"] <= df["bb_lower"], "signal"] = 1
        df.loc[df["close"] >= df["bb_upper"], "signal"] = -1
        prev_signal = df["signal"].shift(1).fillna(0)
        df["signal"] = np.where(df["signal"] != prev_signal, df["signal"], 0)
        return df


class MeanReversion_Strategy(BaseStrategy):
    name = "Mean Reversion"
    description = "Buy when price deviates below the moving average by a threshold, sell when it reverts above."
    category = "mean_reversion"

    @classmethod
    def get_params(cls) -> List[StrategyParam]:
        return [
            StrategyParam("period", "MA Period", "int", 30, min=10, max=200, step=1),
            StrategyParam("threshold", "Deviation Threshold (%)", "float", 2.0, min=0.5, max=10.0, step=0.5),
        ]

    def generate_signals(self, df: pd.DataFrame, params: Dict) -> pd.DataFrame:
        period = params.get("period", 30)
        threshold = params.get("threshold", 2.0) / 100
        df = df.copy()
        df["ma"] = df["close"].rolling(window=period).mean()
        df["deviation"] = (df["close"] - df["ma"]) / df["ma"]
        df["signal"] = 0
        df.loc[df["deviation"] < -threshold, "signal"] = 1
        df.loc[df["deviation"] > threshold, "signal"] = -1
        prev_signal = df["signal"].shift(1).fillna(0)
        df["signal"] = np.where(df["signal"] != prev_signal, df["signal"], 0)
        return df


class Momentum_Strategy(BaseStrategy):
    name = "Momentum"
    description = "Buy when price momentum (rate of change) exceeds threshold, sell when it drops below."
    category = "momentum"

    @classmethod
    def get_params(cls) -> List[StrategyParam]:
        return [
            StrategyParam("period", "Lookback Period", "int", 14, min=5, max=100, step=1),
            StrategyParam("threshold", "ROC Threshold (%)", "float", 2.0, min=0.5, max=10.0, step=0.5),
        ]

    def generate_signals(self, df: pd.DataFrame, params: Dict) -> pd.DataFrame:
        period = params.get("period", 14)
        threshold = params.get("threshold", 2.0) / 100
        df = df.copy()
        df["roc"] = df["close"].pct_change(periods=period)
        df["signal"] = 0
        df.loc[df["roc"] > threshold, "signal"] = 1
        df.loc[df["roc"] < -threshold, "signal"] = -1
        prev_signal = df["signal"].shift(1).fillna(0)
        df["signal"] = np.where(df["signal"] != prev_signal, df["signal"], 0)
        return df


class VWAP_Strategy(BaseStrategy):
    name = "VWAP"
    description = "Buy when price crosses above VWAP, sell when it crosses below. Best for intraday."
    category = "trend"

    @classmethod
    def get_params(cls) -> List[StrategyParam]:
        return [
            StrategyParam("threshold", "Cross Threshold (%)", "float", 0.5, min=0.1, max=3.0, step=0.1),
        ]

    def generate_signals(self, df: pd.DataFrame, params: Dict) -> pd.DataFrame:
        threshold = params.get("threshold", 0.5) / 100
        df = df.copy()
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        df["vwap"] = (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()
        df["signal"] = 0
        deviation = (df["close"] - df["vwap"]) / df["vwap"]
        df.loc[deviation > threshold, "signal"] = 1
        df.loc[deviation < -threshold, "signal"] = -1
        df["signal"] = df["signal"].diff().div(2).fillna(0).astype(int)
        return df


class DCA_Strategy(BaseStrategy):
    name = "Dollar Cost Averaging"
    description = "Buy at regular intervals regardless of price. Optional: increase buy amount on dips."
    category = "passive"

    @classmethod
    def get_params(cls) -> List[StrategyParam]:
        return [
            StrategyParam("interval", "Buy Every N Candles", "int", 24, min=1, max=168, step=1),
            StrategyParam("dip_multiplier", "Dip Buy Multiplier", "float", 1.5, min=1.0, max=3.0, step=0.1),
            StrategyParam("dip_threshold", "Dip Threshold (%)", "float", 5.0, min=1.0, max=20.0, step=1.0),
        ]

    def generate_signals(self, df: pd.DataFrame, params: Dict) -> pd.DataFrame:
        interval = params.get("interval", 24)
        df = df.copy()
        df["signal"] = 0
        # Buy at regular intervals
        buy_indices = list(range(0, len(df), interval))
        df.iloc[buy_indices, df.columns.get_loc("signal")] = 1
        return df


class GridTrading_Strategy(BaseStrategy):
    name = "Grid Trading"
    description = "Place buy/sell orders at fixed price intervals (grid levels). Profits from sideways markets."
    category = "market_making"

    @classmethod
    def get_params(cls) -> List[StrategyParam]:
        return [
            StrategyParam("grid_size", "Grid Size (%)", "float", 2.0, min=0.5, max=10.0, step=0.5),
            StrategyParam("num_grids", "Number of Grid Levels", "int", 5, min=2, max=20, step=1),
        ]

    def generate_signals(self, df: pd.DataFrame, params: Dict) -> pd.DataFrame:
        grid_size = params.get("grid_size", 2.0) / 100
        df = df.copy()
        df["signal"] = 0
        # Calculate grid levels based on the initial price
        base_price = df["close"].iloc[0]
        for i in range(1, len(df)):
            change = (df["close"].iloc[i] - base_price) / base_price
            if change < -grid_size:
                df.iloc[i, df.columns.get_loc("signal")] = 1  # Buy on drop
                base_price = df["close"].iloc[i]
            elif change > grid_size:
                df.iloc[i, df.columns.get_loc("signal")] = -1  # Sell on rise
                base_price = df["close"].iloc[i]
        return df


# Registry of all strategies
STRATEGY_REGISTRY: Dict[str, type] = {
    "sma_crossover": SMA_Crossover,
    "ema_crossover": EMA_Crossover,
    "rsi": RSI_Strategy,
    "macd": MACD_Strategy,
    "bollinger_bands": BollingerBands_Strategy,
    "mean_reversion": MeanReversion_Strategy,
    "momentum": Momentum_Strategy,
    "vwap": VWAP_Strategy,
    "dca": DCA_Strategy,
    "grid_trading": GridTrading_Strategy,
    "pure_ai": PureAI_Strategy,
}


def get_strategy(name: str) -> BaseStrategy:
    """Get a strategy instance by key or display name."""
    cls = STRATEGY_REGISTRY.get(name)
    if not cls:
        # Try matching by display name
        for key, strategy_cls in STRATEGY_REGISTRY.items():
            if strategy_cls.name == name:
                cls = strategy_cls
                break
    if not cls:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGY_REGISTRY.keys())}")
    return cls()


def list_strategies() -> List[Dict]:
    """Return info for all available strategies."""
    return [cls.info() for cls in STRATEGY_REGISTRY.values()]
