"""Fetch real 三大法人買賣超 (institutional net buy/sell) data from TWSE's public
T86 endpoint for a single stock. Returns None on any failure (network, symbol
not found, unexpected response shape) so callers can just omit the table
rather than fabricate numbers.
"""

import requests

TWSE_T86_URL = "https://www.twse.com.tw/rwd/zh/fund/T86"


def _find_col(fields: list[str], *keywords: str) -> int | None:
    for i, f in enumerate(fields):
        if all(k in f for k in keywords):
            return i
    return None


def _to_lots(row: list, idx: int | None) -> int | None:
    if idx is None or idx >= len(row):
        return None
    try:
        return round(int(str(row[idx]).replace(",", "").strip()) / 1000)
    except (ValueError, TypeError):
        return None


def fetch_institutional_flow(symbol: str, trade_date: str) -> dict | None:
    """symbol: plain numeric stock code (no .TW suffix). trade_date: 'YYYY-MM-DD'."""
    try:
        resp = requests.get(
            TWSE_T86_URL,
            params={"date": trade_date.replace("-", ""), "selectType": "ALL", "response": "json"},
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        print(f"warning: TWSE institutional flow request failed for {symbol}: {exc}")
        return None

    if payload.get("stat") != "OK":
        print(f"warning: TWSE institutional flow returned stat={payload.get('stat')} for {trade_date}")
        return None

    fields = payload.get("fields", [])
    rows = payload.get("data", [])

    code_col = _find_col(fields, "證券代號")
    foreign_col = _find_col(fields, "外陸資買賣超股數")
    trust_col = _find_col(fields, "投信買賣超股數")
    dealer_col = _find_col(fields, "自營商買賣超股數")
    total_col = _find_col(fields, "三大法人買賣超股數")

    if code_col is None:
        print("warning: could not locate 證券代號 column in TWSE T86 response")
        return None

    for row in rows:
        if len(row) > code_col and str(row[code_col]).strip() == symbol:
            return {
                "foreign": _to_lots(row, foreign_col),
                "trust": _to_lots(row, trust_col),
                "dealer": _to_lots(row, dealer_col),
                "total": _to_lots(row, total_col),
            }

    print(f"warning: symbol {symbol} not found in TWSE T86 data for {trade_date}")
    return None


def fetch_institutional_flow_range(symbol: str, trade_dates: list[str]) -> dict | None:
    """Sum real per-day TWSE net buy/sell across trade_dates (e.g. one
    report's trading week), instead of returning a single day's snapshot
    that may not represent the period the report is actually covering.

    A day TWSE has no data for (not yet published, holiday quirk) is
    skipped rather than counted as zero. Returns None only if every day
    failed, so callers can omit the table instead of showing a fabricated
    or misleadingly partial figure. days_matched/days_requested are
    included so a partial week (e.g. today's data not published yet) is
    visible rather than silently presented as a full one.
    """
    totals = {"foreign": 0, "trust": 0, "dealer": 0, "total": 0}
    matched_days = 0
    for trade_date in trade_dates:
        day = fetch_institutional_flow(symbol, trade_date)
        if day is None:
            continue
        matched_days += 1
        for key in totals:
            if day.get(key) is not None:
                totals[key] += day[key]

    if matched_days == 0:
        return None

    totals["days_matched"] = matched_days
    totals["days_requested"] = len(trade_dates)
    return totals
