"""Compute RS/position data (code) and generate the committee narrative (Claude) per target."""

import json
import os
import pathlib
from datetime import date

import anthropic

import lib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
SYSTEM_PROMPT_PATH = BASE_DIR / "prompts" / "system_prompt.md"
MUST_WATCH_PATH = BASE_DIR / "config" / "must_watch.json"
ARCHIVE_DIR = BASE_DIR / "reports"
OUTPUT_DIR = BASE_DIR / "output"

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")
DISCLAIMER = "投資一定有風險，基金/ETF/股票投資有賺有賠，以上資訊非投資建議"


def load_targets() -> list:
    main = os.environ.get("MAIN", "").strip()
    if main:
        compare_raw = os.environ.get("COMPARE", "")
        compare = [s.strip() for s in compare_raw.split(",") if s.strip()]
        return [{"main": main, "compare": compare, "label": main}]
    return json.loads(MUST_WATCH_PATH.read_text(encoding="utf-8"))


def ensure_disclaimer(text: str) -> str:
    if DISCLAIMER in text:
        return text
    print("warning: disclaimer missing from model output, appending it")
    return text.rstrip() + "\n\n" + DISCLAIMER


def generate_one(target: dict, client: anthropic.Anthropic, system_prompt: str, use_web_search: bool, params: dict) -> str:
    data = lib.build_committee_data(
        main=target["main"],
        compare=target.get("compare", []),
        rs_lookback_days=params["rs_lookback"],
        rs_pass_threshold=params["rs_pass"],
        capital_twd=params["capital"],
        risk_pct=params["risk_pct"],
        stop_loss_pct=params["stop_loss_pct"],
        target_pct=params["target_pct"],
    )

    display_main = target["main"].removesuffix(".TW").removesuffix(".TWO")
    user_content = (
        f"以下是 {display_main}（{lib.symbol_name(target['main'])}）的委員會分析資料（JSON），"
        "請依照系統提示撰寫報告：\n\n" + json.dumps(data, ensure_ascii=False, indent=2)
    )

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

    report_text = "".join(block.text for block in response.content if block.type == "text").strip()
    return ensure_disclaimer(report_text)


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

    for target in targets:
        print(f"generating report for {target['main']}...")
        report_text = generate_one(target, client, system_prompt, use_web_search, params)

        safe_symbol = target["main"].replace(".", "_")
        archive_path = ARCHIVE_DIR / f"{safe_symbol}_{today}.md"
        archive_path.write_text(report_text, encoding="utf-8")

        output_path = OUTPUT_DIR / f"{safe_symbol}.txt"
        output_path.write_text(report_text, encoding="utf-8")

        print(f"wrote {archive_path} and {output_path}")


if __name__ == "__main__":
    main()
