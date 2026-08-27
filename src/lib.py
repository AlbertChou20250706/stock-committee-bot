"""RS momentum and position-sizing math, computed from real price history (not LLM-guessed)."""

import json
import math
import pathlib

import yfinance as yf

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
SYMBOL_NAMES_PATH = BASE_DIR / "config" / "symbol_names.json"

_symbol_names = json.loads(SYMBOL_NAMES_PATH.read_text(encoding="utf-8"))


def symbol_name(symbol: str) -> str:
    return _symbol_names.get(symbol, symbol)


def rs_return(symbol: str, lookback_days: int) -> dict:
    """RS 區間累積報酬率 = (最新收盤價 - 回看起始收盤價) / 回看起始收盤價 * 100."""
    history = yf.Ticker(symbol).history(period=f"{lookback_days + 15}d")
    window = history.tail(lookback_days + 1)
    if len(window) < lookback_days + 1:
        raise RuntimeError(
            f"not enough price history for {symbol}: need {lookback_days + 1} rows, got {len(window)}"
        )

    baseline_close = float(window["Close"].iloc[0])
    latest_close = float(window["Close"].iloc[-1])
    rs_pct = (latest_close - baseline_close) / baseline_close * 100

    return {
        "symbol": symbol,
        "name": symbol_name(symbol),
        "date_start": window.index[0].strftime("%Y-%m-%d"),
        "date_end": window.index[-1].strftime("%Y-%m-%d"),
        "baseline_close": round(baseline_close, 2),
        "latest_close": round(latest_close, 2),
        "rs_return_pct": round(rs_pct, 2),
    }


def compute_position(
    entry_price: float,
    capital_twd: float,
    risk_pct: float,
    stop_loss_pct: float,
    target_pct: float,
) -> dict:
    stop_loss_price = round(entry_price * (1 - stop_loss_pct / 100), 2)
    per_share_risk = round(entry_price - stop_loss_price, 2)
    risk_twd = round(capital_twd * risk_pct / 100, 2)
    max_shares = math.floor(risk_twd / per_share_risk) if per_share_risk > 0 else 0
    target_price = round(entry_price * (1 + target_pct / 100), 2)

    return {
        "capital_twd": capital_twd,
        "risk_pct": risk_pct,
        "risk_twd": risk_twd,
        "stop_loss_pct": stop_loss_pct,
        "stop_loss_price": stop_loss_price,
        "per_share_risk": per_share_risk,
        "max_shares": max_shares,
        "position_cost_twd": round(max_shares * entry_price, 2),
        "target_pct": target_pct,
        "target_price": target_price,
    }


def build_committee_data(
    main: str,
    compare: list[str],
    rs_lookback_days: int,
    rs_pass_threshold: int,
    capital_twd: float,
    risk_pct: float,
    stop_loss_pct: float,
    target_pct: float,
) -> dict:
    main_data = rs_return(main, rs_lookback_days)

    compare_data = []
    for symbol in compare:
        try:
            compare_data.append(rs_return(symbol, rs_lookback_days))
        except RuntimeError as exc:
            print(f"warning: skipping COMPARE symbol {symbol}: {exc}")

    rs_pass_count = sum(1 for c in compare_data if main_data["rs_return_pct"] > c["rs_return_pct"])

    position = compute_position(
        entry_price=main_data["latest_close"],
        capital_twd=capital_twd,
        risk_pct=risk_pct,
        stop_loss_pct=stop_loss_pct,
        target_pct=target_pct,
    )

    return {
        "main": main_data,
        "compare": compare_data,
        "rs_lookback_days": rs_lookback_days,
        "rs_pass_threshold": rs_pass_threshold,
        "rs_pass_count": rs_pass_count,
        "rs_passed": rs_pass_count >= rs_pass_threshold,
        "risk": position,
    }
