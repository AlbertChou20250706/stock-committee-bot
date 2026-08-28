"""Render a real candlestick chart (yfinance OHLC data, not AI-drawn) for each
committee target's MAIN symbol. Must run — and its output be committed/pushed —
before run_committee.py builds any Flex Message, since the Flex hero image
references the chart via a raw.githubusercontent.com URL.
"""

import pathlib
from datetime import date

import mplfinance as mpf
import yfinance as yf

import lib
from targets import load_targets

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
CHARTS_DIR = BASE_DIR / "charts"

LOOKBACK = "3mo"

# GitHub Actions' ubuntu-latest has no CJK font by default; without this the
# Chinese title renders as tofu boxes (font installed via apt in the workflow:
# fonts-wqy-zenhei). Plain pyplot.rcParams doesn't work here — mplfinance
# builds its own rc context from the style, so the font must be set via
# make_mpf_style(rc=...) instead.
TW_STYLE = mpf.make_mpf_style(
    marketcolors=mpf.make_marketcolors(up="red", down="green", inherit=True),
    gridstyle="",
    facecolor="white",
    rc={"font.sans-serif": ["WenQuanYi Zen Hei"], "axes.unicode_minus": False},
)


def render_chart(symbol: str) -> None:
    history = yf.Ticker(symbol).history(period=LOOKBACK)
    if history.empty:
        raise RuntimeError(f"no usable price history for {symbol}")

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_symbol = symbol.replace(".", "_")
    today = date.today().isoformat()
    chart_path = CHARTS_DIR / f"{safe_symbol}_{today}.png"

    display_symbol = symbol.removesuffix(".TW").removesuffix(".TWO")
    name = lib.symbol_name(symbol)

    mpf.plot(
        history,
        type="candle",
        style=TW_STYLE,
        volume=True,
        figsize=(9, 5.5),
        title=f"\n{name}（{display_symbol}）",
        savefig=dict(fname=chart_path, dpi=150, bbox_inches="tight"),
    )
    print(f"wrote {chart_path}")


def main() -> None:
    for target in load_targets():
        render_chart(target["main"])


if __name__ == "__main__":
    main()
