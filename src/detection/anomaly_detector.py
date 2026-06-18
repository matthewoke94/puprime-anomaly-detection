import logging
import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import random
import uuid

fake = Faker()
random.seed(42)

logger = logging.getLogger(__name__)


def generate_trade_events(n: int = 1000) -> pd.DataFrame:
    """
    Generate simulated trade events with some anomalies injected.

    Anomaly types:
        - unusual_volume: lot size > 10 (normal max is 5)
        - rapid_trading: more than 5 trades in 10 minutes
        - large_transaction: deposit/withdrawal > $50,000
        - loss_streak: 5 consecutive losing trades
    """
    trader_ids = [str(uuid.uuid4()) for _ in range(50)]
    events = []

    for i in range(n):
        trader_id = random.choice(trader_ids)
        timestamp = fake.date_time_between(start_date="-30d", end_date="now")

        # Inject anomalies in ~5% of events
        is_anomaly = random.random() < 0.05
        lot_size = round(random.uniform(15.0, 50.0), 2) if is_anomaly else round(random.uniform(0.01, 5.0), 2)

        events.append({
            "event_id": str(uuid.uuid4()),
            "trader_id": trader_id,
            "symbol": random.choice(["EUR/USD", "GBP/USD", "USD/JPY", "XAU/USD"]),
            "direction": random.choice(["buy", "sell"]),
            "lot_size": lot_size,
            "price": round(random.uniform(1.0, 200.0), 5),
            "profit_loss": round(random.uniform(-500, 500), 2),
            "timestamp": timestamp,
            "is_anomaly": is_anomaly,
        })

    return pd.DataFrame(events).sort_values("timestamp").reset_index(drop=True)


def detect_unusual_volume(df: pd.DataFrame, threshold: float = 10.0) -> pd.DataFrame:
    """Flag trades with unusually large lot sizes."""
    flagged = df[df["lot_size"] > threshold].copy()
    flagged["alert_type"] = "unusual_volume"
    flagged["alert_reason"] = flagged["lot_size"].apply(
        lambda x: f"Lot size {x} exceeds threshold {threshold}"
    )
    logger.info(f"Unusual volume alerts: {len(flagged)}")
    return flagged


def detect_rapid_trading(df: pd.DataFrame, window_minutes: int = 10, max_trades: int = 5) -> pd.DataFrame:
    """Flag traders executing too many trades in a short window."""
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    alerts = []

    for trader_id, group in df.groupby("trader_id"):
        group = group.sort_values("timestamp")
        for i, row in group.iterrows():
            window_end = row["timestamp"] + timedelta(minutes=window_minutes)