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


def generate_trade_events(n=1000):
    trader_ids = [str(uuid.uuid4()) for _ in range(50)]
    events = []
    for i in range(n):
        trader_id = random.choice(trader_ids)
        timestamp = fake.date_time_between(start_date="-30d", end_date="now")
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


def detect_unusual_volume(df, threshold=10.0):
    flagged = df[df["lot_size"] > threshold].copy()
    flagged["alert_type"] = "unusual_volume"
    flagged["alert_reason"] = flagged["lot_size"].apply(
        lambda x: f"Lot size {x} exceeds threshold {threshold}"
    )
    logger.info(f"Unusual volume alerts: {len(flagged)}")
    return flagged


def detect_rapid_trading(df, window_minutes=10, max_trades=5):
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    alerts = []
    for trader_id, group in df.groupby("trader_id"):
        group = group.sort_values("timestamp")
        for i, row in group.iterrows():
            window_end = row["timestamp"] + timedelta(minutes=window_minutes)
            trades_in_window = group[
                (group["timestamp"] >= row["timestamp"]) &
                (group["timestamp"] <= window_end)
            ]
            if len(trades_in_window) > max_trades:
                alert = row.copy()
                alert["alert_type"] = "rapid_trading"
                alert["alert_reason"] = f"{len(trades_in_window)} trades in {window_minutes} min window"
                alerts.append(alert)
                break
    if alerts:
        return pd.DataFrame(alerts)
    return pd.DataFrame(columns=df.columns.tolist() + ["alert_type", "alert_reason"])


def detect_loss_streak(df, streak_length=5):
    df = df.copy()
    alerts = []
    for trader_id, group in df.groupby("trader_id"):
        group = group.sort_values("timestamp").reset_index(drop=True)
        streak = 0
        for i, row in group.iterrows():
            if row["profit_loss"] < 0:
                streak += 1
                if streak >= streak_length:
                    alert = row.copy()
                    alert["alert_type"] = "loss_streak"
                    alert["alert_reason"] = f"{streak} consecutive losing trades"
                    alerts.append(alert)
            else:
                streak = 0
    if alerts:
        return pd.DataFrame(alerts)
    return pd.DataFrame(columns=df.columns.tolist() + ["alert_type", "alert_reason"])


def run_all_detectors(df):
    volume_alerts = detect_unusual_volume(df)
    rapid_alerts = detect_rapid_trading(df)
    streak_alerts = detect_loss_streak(df)
    all_alerts = pd.concat(
        [volume_alerts, rapid_alerts, streak_alerts], ignore_index=True
    )
    logger.info(f"Total alerts generated: {len(all_alerts)}")
    return all_alerts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    events = generate_trade_events(1000)
    print(f"Generated {len(events)} trade events")
    alerts = run_all_detectors(events)
    print(f"Total alerts: {len(alerts)}")
    print(alerts["alert_type"].value_counts())
