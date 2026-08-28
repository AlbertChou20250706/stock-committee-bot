"""Compute RS/risk/institutional data (code) and generate the committee
narrative (Claude) per target, then build a LINE Flex Message card (chart +
tables + narrative) for each. Falls back to plain text per-target if the
model doesn't follow the delimiter format, so a report still goes out either
way. Writes output/targets.json listing every processed target so send_line.py
knows what to send without having to rediscover it from filenames.
"""

import json
import os
import pathlib
from datetime import date

import anthropic

import build_flex
import lib
from parse_committee import parse_sections
from targets import load_targets

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
SYSTEM_PROMPT_PATH = BASE_DIR / "prompts" / "system_prompt.md"
ARCHIVE_DIR = BASE_DIR / "reports"
OUTPUT_DIR = BASE_DIR / "output"

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")
DISCLAIMER = "投資一定有風險，基金/ETF/股票投資有賺有賠，以上資訊非投資建議"


def build_user_content(target: dict, computed: dict) -> str:
    display_main = target["main"].removesuffix(".TW").removesuffix(".TWO")
    return (
        f"以下是 {display_main}（{lib.symbol_name(target['main'])}）的委員會分析資料（JSON），"
        "請依照系統提示撰寫報告：\n\n" + json.dumps(computed, ensure_ascii=False, indent=2)
    )


def call_model(client: anthropic.Anthropic, system_prompt: str, user_content: str, use_web_search: bool) -> str:
    request_kwargs = dict(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": "medium"},
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    if use_web_search:
        request_kwargs["tools"] = [{
            "type": "web_search_20260209",
            "name": "web_search",
            "max_uses": 3,
            "allowed_domains": [
                "tw.stock.yahoo.com",
                "cnyes.com",
                "money.udn.com",
                "ctee.com.tw",
                "moneydj.com",
                "goodinfo.tw",
                "statementdog.com",
            ],
        }]
    response = client.messages.create(**request_kwargs)
    return "".join(block.text for block in response.content if block.type == "text").strip()


def render_markdown(computed: dict, parsed: dict) -> str:
    main = computed["main"]
    risk = computed["risk"]
    lines = [f"AI 股市投資決策委員會 — {main['name']}（{main['symbol']}）", f"資料截至 {main['date_end']}", ""]
    lines += [f"RS 報酬率（近{computed['rs_lookback_days']}交易日）：{main['rs_return_pct']}%"]

    inst = main.get("institutional")
    if inst and inst.get("total") is not None:
        lines += [
            f"三大法人（張）：外資 {inst.get('foreign', 0):+,} / 投信 {inst.get('trust', 0):+,} "
            f"/ 自營 {inst.get('dealer', 0):+,} ｜ 合計 {inst['total']:+,}"
        ]

    lines += [
        f"RS 動能濾網：{'通過' if computed['rs_passed'] else '未通過'}"
        f"（{computed['rs_pass_count']}/{len(computed['compare'])}，門檻 {computed['rs_pass_threshold']}）",
        "",
    ]

    if computed["compare"]:
        lines += ["相對強弱比較組："]
        lines += [f"　{c['symbol']} {c['name']}：{c['rs_return_pct']}%" for c in computed["compare"]]
        lines += [""]

    lines += [
        "量化風控數據（程式精算）：",
        f"　止損價：{risk['stop_loss_price']} 元",
        f"　每股風險：{risk['per_share_risk']} 元",
        f"　可承受風險金額：{risk['risk_twd']:,.0f} 元",
        f"　建議可買股數：{risk['max_shares']:,} 股",
        f"　目標價：{risk['target_price']} 元",
        "",
    ]

    lines += ["## 股票基本盤勢", parsed["basic"], ""]
    lines += ["## 核心策略分析", parsed["strategy"], ""]
    lines += ["## 風險提示", parsed["risk_note"], ""]

    if parsed["news"]:
        lines += ["## 相關新聞來源"]
        lines += [f"{n['title']}\n{n['url']}" for n in parsed["news"]]
        lines += [""]

    lines += [parsed["disclaimer"]]
    return "\n".join(lines)


def process_target(
    target: dict,
    client: anthropic.Anthropic,
    system_prompt: str,
    use_web_search: bool,
    params: dict,
    today: str,
) -> str:
    computed = lib.build_committee_data(
        main=target["main"],
        compare=target.get("compare", []),
        rs_lookback_days=params["rs_lookback"],
        rs_pass_threshold=params["rs_pass"],
        capital_twd=params["capital"],
        risk_pct=params["risk_pct"],
        stop_loss_pct=params["stop_loss_pct"],
        target_pct=params["target_pct"],
    )
    raw_text = call_model(client, system_prompt, build_user_content(target, computed), use_web_search)

    safe_symbol = target["main"].replace(".", "_")
    parsed = parse_sections(raw_text)

    if parsed is None:
        print(f"warning: could not parse structured sections for {target['main']}, falling back to plain text")
        report_text = raw_text if DISCLAIMER in raw_text else raw_text.rstrip() + "\n\n" + DISCLAIMER
        (ARCHIVE_DIR / f"{safe_symbol}_{today}.md").write_text(report_text, encoding="utf-8")
        (OUTPUT_DIR / f"{safe_symbol}.txt").write_text(report_text, encoding="utf-8")
        return safe_symbol

    parsed["disclaimer"] = DISCLAIMER
    archive_text = render_markdown(computed, parsed)
    (ARCHIVE_DIR / f"{safe_symbol}_{today}.md").write_text(archive_text, encoding="utf-8")

    build_flex.build_message(target["main"], computed, parsed, OUTPUT_DIR / f"{safe_symbol}_flex.json")
    return safe_symbol


def main() -> None:
    targets = load_targets()
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    client = anthropic.Anthropic()

    params = {
        "rs_lookback": int(os.environ.get("RS_LOOKBACK", "25")),
        "rs_pass": int(os.environ.get("RS_PASS", "2")),
        "capital": float(os.environ.get("CAPITAL", "200000")),
        "risk_pct": float(os.environ.get("RISK_PCT", "2")),
        "stop_loss_pct": float(os.environ.get("STOP_LOSS_PCT", "8")),
        "target_pct": float(os.environ.get("TARGET_PCT", "20")),
    }
    use_web_search = os.environ.get("USE_WEB_SEARCH", "true").lower() == "true"

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()

    processed = []
    for target in targets:
        print(f"generating report for {target['main']}...")
        safe_symbol = process_target(target, client, system_prompt, use_web_search, params, today)
        processed.append(safe_symbol)
        print(f"done with {safe_symbol}")

    (OUTPUT_DIR / "targets.json").write_text(json.dumps(processed, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUTPUT_DIR / 'targets.json'}")


if __name__ == "__main__":
    main()
