import logging
import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")


def create_alerts_table(conn):
    query = (
        "CREATE TABLE IF NOT EXISTS trading_alerts ("
        "id SERIAL PRIMARY KEY, "
        "event_id VARCHAR(36), "
        "trader_id VARCHAR(36) NOT NULL, "
        "symbol VARCHAR(20), "
        "alert_type VARCHAR(50) NOT NULL, "
        "alert_reason TEXT NOT NULL, "
        "lot_size NUMERIC(10, 2), "
        "profit_loss NUMERIC(10, 2), "
        "timestamp TIMESTAMP, "
        "created_at TIMESTAMP DEFAULT NOW(), "
        "UNIQUE(event_id, alert_type)"
        ");"
    )
    with conn.cursor() as cur:
        cur.execute(query)
    conn.commit()
    logger.info("Alerts table ready.")


def save_alerts(alerts_df):
    result = {"attempted": 0, "inserted": 0, "skipped_duplicates": 0}

    if alerts_df is None or alerts_df.empty:
        logger.warning("No alerts to save.")
        return result

    if not DATABASE_URL:
        logger.error("DATABASE_URL not found.")
        return result

    try:
        conn = psycopg2.connect(DATABASE_URL)
        create_alerts_table(conn)

        records = [
            (
                str(row.event_id) if hasattr(row, "event_id") and pd.notna(row.event_id) else None,
                str(row.trader_id),
                str(row.symbol) if hasattr(row, "symbol") and pd.notna(row.symbol) else None,
                str(row.alert_type),
                str(row.alert_reason),
                float(row.lot_size) if hasattr(row, "lot_size") and pd.notna(row.lot_size) else None,
                float(row.profit_loss) if hasattr(row, "profit_loss") and pd.notna(row.profit_loss) else None,
                pd.to_datetime(row.timestamp) if hasattr(row, "timestamp") and pd.notna(row.timestamp) else None,
            )
            for row in alerts_df.itertuples()
        ]
        result["attempted"] = len(records)

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM trading_alerts;")
            before_count = cur.fetchone()[0]

        insert_query = (
            "INSERT INTO trading_alerts ("
            "event_id, trader_id, symbol, alert_type, "
            "alert_reason, lot_size, profit_loss, timestamp"
            ") VALUES %s "
            "ON CONFLICT (event_id, alert_type) DO NOTHING;"
        )

        with conn.cursor() as cur:
            execute_values(cur, insert_query, records)

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM trading_alerts;")
            after_count = cur.fetchone()[0]

        conn.commit()
        conn.close()

        result["inserted"] = after_count - before_count
        result["skipped_duplicates"] = result["attempted"] - result["inserted"]

        logger.info(
            f"Saved {result['inserted']} new alerts, "
            f"{result['skipped_duplicates']} duplicates skipped "
            f"(of {result['attempted']} attempted)."
        )
        return result

    except Exception as e:
        logger.error(f"Failed to save alerts: {e}")
        raise


def run_pipeline():
    import sys
    sys.path.append("/workspaces/puprime-anomaly-detection")
    from src.detection.anomaly_detector import generate_trade_events, run_all_detectors

    logger.info("Starting anomaly detection pipeline...")
    events = generate_trade_events(1000)
    logger.info(f"Generated {len(events)} trade events")

    alerts = run_all_detectors(events)
    logger.info(f"Detected {len(alerts)} alerts")

    result = save_alerts(alerts)

    if not alerts.empty:
        print("\n=== Alert Summary ===")
        print(alerts["alert_type"].value_counts())
        print(f"\nLoad result: {result}")

    return result


if __name__ == "__main__":
    run_pipeline()
