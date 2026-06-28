Run:
```bash
python src/pipeline/alerts_pipeline.py
```

## Known gaps / next steps

- Detectors run on simulated data — in production, events would come from a real-time trade stream (Kafka or a database change feed)
- `detect_rapid_trading()` uses an O(n²) per-trader window scan — acceptable for this scale, would need optimization for millions of events
- No alerting/notification layer yet — alerts exist in the database but nothing pings the compliance team automatically
- Thresholds (lot size > 10, window = 10 minutes, streak = 5) are hardcoded — a production system would make these configurable per instrument

## Business value

This pipeline is the foundation of a risk monitoring system. For a broker like PuPrime, catching an overleveraged position early prevents both client losses and potential regulatory liability. The queryable alerts table means compliance teams can filter, audit, and report on flagged activity without touching raw trade data.

## Author

Matthew James — Data Engineer
GitHub: github.com/matthewoke94