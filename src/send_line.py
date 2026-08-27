"""Push every generated report in output/ to one or more LINE targets (users or groups)."""

import os
import pathlib

import requests

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def push_message(token: str, target_id: str, text: str) -> None:
    response = requests.post(
        LINE_PUSH_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"to": target_id, "messages": [{"type": "text", "text": text}]},
        timeout=30,
    )
    response.raise_for_status()


def main() -> None:
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    target_ids = [t.strip() for t in os.environ["LINE_PUSH_TARGET_IDS"].split(",") if t.strip()]
    if not target_ids:
        raise RuntimeError("LINE_PUSH_TARGET_IDS is empty")

    report_files = sorted(OUTPUT_DIR.glob("*.txt"))
    if not report_files:
        raise RuntimeError(f"no report files found in {OUTPUT_DIR}")

    for report_file in report_files:
        report_text = report_file.read_text(encoding="utf-8")
        for target_id in target_ids:
            push_message(token, target_id, report_text)
            print(f"sent {report_file.name} to {target_id}")


if __name__ == "__main__":
    main()
