"""Push each committee target's report to one or more LINE targets (users or
groups). Reads output/targets.json (written by run_committee.py) to know
which targets were processed this run, then sends each as a Flex Message if
output/<safe>_flex.json exists, otherwise falls back to output/<safe>.txt as
plain text.
"""

import json
import os
import pathlib

import requests

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
TARGETS_PATH = OUTPUT_DIR / "targets.json"

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def push(token: str, target_id: str, message: dict) -> None:
    response = requests.post(
        LINE_PUSH_URL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"to": target_id, "messages": [message]},
        timeout=30,
    )
    response.raise_for_status()


def main() -> None:
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    target_ids = [t.strip() for t in os.environ["LINE_PUSH_TARGET_IDS"].split(",") if t.strip()]
    if not target_ids:
        raise RuntimeError("LINE_PUSH_TARGET_IDS is empty")

    if not TARGETS_PATH.exists():
        raise RuntimeError(f"{TARGETS_PATH} not found; run_committee.py must run first")
    safe_symbols = json.loads(TARGETS_PATH.read_text(encoding="utf-8"))
    if not safe_symbols:
        raise RuntimeError("no targets were processed")

    for safe_symbol in safe_symbols:
        flex_path = OUTPUT_DIR / f"{safe_symbol}_flex.json"
        text_path = OUTPUT_DIR / f"{safe_symbol}.txt"
        if flex_path.exists():
            message = json.loads(flex_path.read_text(encoding="utf-8"))
        elif text_path.exists():
            message = {"type": "text", "text": text_path.read_text(encoding="utf-8")}
        else:
            print(f"warning: no output found for {safe_symbol}, skipping")
            continue
        for target_id in target_ids:
            push(token, target_id, message)
            print(f"sent {safe_symbol} to {target_id}")


if __name__ == "__main__":
    main()
