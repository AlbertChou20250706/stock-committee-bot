"""Build one LINE Flex Message (card layout) per committee target, combining
the code-computed RS/risk/institutional data with the model's narrative and
that target's chart image (already committed + pushed by generate_chart.py
before this runs). Imported directly by run_committee.py per target rather
than run standalone, since each target's computed/parsed data only exists
in-process there.
"""

import json
import os
import pathlib
from datetime import date

UP_COLOR = "#D32F2F"    # TW convention: red = up
DOWN_COLOR = "#2E7D32"  # TW convention: green = down
HEADER_BG = "#1A2942"
MUTED = "#666666"
INK = "#222222"


def change_color(value) -> str:
    try:
        return UP_COLOR if float(value) >= 0 else DOWN_COLOR
    except (TypeError, ValueError):
        return INK


def chart_url(safe_symbol: str) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "AlbertChou20250706/stock-committee-bot")
    today = date.today().isoformat()
    return f"https://raw.githubusercontent.com/{repo}/main/charts/{safe_symbol}_{today}.png"


def text(content: str, **kwargs) -> dict:
    return {"type": "text", "text": content, "wrap": True, **kwargs}


def separator() -> dict:
    return {"type": "separator", "margin": "lg"}


def section_title(label: str) -> dict:
    return text(label, weight="bold", size="md", margin="lg", color=INK)


def institutional_line(inst: dict | None) -> dict | None:
    if not inst or inst.get("total") is None:
        return None
    parts = []
    for label, key in [("外資", "foreign"), ("投信", "trust"), ("自營", "dealer")]:
        v = inst.get(key)
        if v is not None:
            parts.append(f"{label} {v:+,}")
    if not parts:
        return None
    total = inst["total"]
    return text(
        f"三大法人（張）：{' / '.join(parts)} ｜ 合計 {total:+,}",
        size="xxs",
        color=change_color(total) if total != 0 else MUTED,
        margin="xs",
    )


def kv_row(label: str, value: str, value_color: str = INK) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "margin": "sm",
        "contents": [
            text(label, size="sm", color=MUTED, flex=2),
            text(value, size="sm", align="end", weight="bold", color=value_color, flex=3),
        ],
    }


def compare_row(c: dict) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "margin": "sm",
        "contents": [
            text(f"{c['symbol']} {c['name']}", size="sm", color=INK, flex=3),
            text(f"{c['rs_return_pct']}%", size="sm", align="end", weight="bold",
                 color=change_color(c["rs_return_pct"]), flex=1),
        ],
    }


def news_row(n: dict) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "margin": "sm",
        "action": {"type": "uri", "uri": n["url"]},
        "contents": [text(f"🔗 {n['title']}", size="sm", color="#2563EB", wrap=True)],
    }


def build_bubble(safe_symbol: str, computed: dict, parsed: dict) -> dict:
    main = computed["main"]
    risk = computed["risk"]

    pass_badge = "✅ 通過 RS 動能濾網" if computed["rs_passed"] else "⚠️ 未通過 RS 動能濾網"
    pass_color = UP_COLOR if computed["rs_passed"] else MUTED

    body_contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                text(f"{main['symbol']} {main['name']}", size="sm", color=MUTED, flex=1),
                text(f"{main['latest_close']}", size="xxl", weight="bold", align="end", color=INK, flex=2),
            ],
        },
        text(
            f"{'▲' if main['rs_return_pct'] >= 0 else '▼'} RS {main['rs_return_pct']}%"
            f"（近{computed['rs_lookback_days']}交易日）",
            align="end", weight="bold", size="md", color=change_color(main["rs_return_pct"]),
        ),
    ]
    inst_line = institutional_line(main.get("institutional"))
    if inst_line:
        body_contents.append(inst_line)

    body_contents += [
        separator(),
        text(pass_badge, weight="bold", size="sm", color=pass_color, margin="md"),
        text(
            f"對比組通過數：{computed['rs_pass_count']} / {len(computed['compare'])}（門檻 {computed['rs_pass_threshold']}）",
            size="xs", color=MUTED, margin="xs",
        ),
    ]

    if computed["compare"]:
        body_contents += [separator(), section_title("相對強弱比較組")]
        body_contents += [compare_row(c) for c in computed["compare"]]

    body_contents += [
        separator(),
        section_title("量化風控數據（程式精算）"),
        kv_row("止損價", f"{risk['stop_loss_price']} 元", DOWN_COLOR),
        kv_row("每股風險", f"{risk['per_share_risk']} 元"),
        kv_row("可承受風險金額", f"{risk['risk_twd']:,.0f} 元"),
        kv_row("建議可買股數", f"{risk['max_shares']:,} 股"),
        kv_row("目標價", f"{risk['target_price']} 元", UP_COLOR),
    ]

    body_contents += [separator(), section_title("股票基本盤勢"),
                       text(parsed["basic"], size="sm", color=INK, margin="sm")]
    body_contents += [separator(), section_title("核心策略分析"),
                       text(parsed["strategy"], size="sm", color=INK, margin="sm")]
    body_contents += [separator(), section_title("風險提示"),
                       text(parsed["risk_note"], size="sm", color=INK, margin="sm")]

    if parsed["news"]:
        body_contents += [separator(), section_title("相關新聞來源")]
        body_contents += [news_row(n) for n in parsed["news"]]

    body_contents += [
        {
            "type": "box",
            "layout": "vertical",
            "margin": "lg",
            "paddingAll": "10px",
            "backgroundColor": "#FFF4E5",
            "cornerRadius": "8px",
            "contents": [text(f"⚠️ {parsed['disclaimer']}", size="xxs", color="#92400E", wrap=True)],
        }
    ]

    return {
        "type": "bubble",
        "size": "giga",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": HEADER_BG,
            "paddingAll": "16px",
            "contents": [
                text(f"{main['name']}（{main['symbol']}）投資委員會報告", color="#FFFFFF", size="xl",
                     weight="bold", wrap=True),
                text(f"資料截至 {main['date_end']}", color="#A8B8D0", size="xs", margin="xs"),
            ],
        },
        "hero": {
            "type": "image",
            "url": chart_url(safe_symbol),
            "size": "full",
            "aspectRatio": "20:13",
            "aspectMode": "fit",
            "backgroundColor": "#FFFFFF",
        },
        "body": {"type": "box", "layout": "vertical", "contents": body_contents},
    }


def build_message(main_symbol: str, computed: dict, parsed: dict, out_path: pathlib.Path) -> None:
    safe_symbol = main_symbol.replace(".", "_")
    flex_message = {
        "type": "flex",
        "altText": f"{computed['main']['name']}（{computed['main']['symbol']}）投資委員會報告",
        "contents": build_bubble(safe_symbol, computed, parsed),
    }
    out_path.write_text(json.dumps(flex_message, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")
