"""Shared target-list loading for run_committee.py and generate_chart.py, so
both scripts agree on which MAIN/COMPARE symbols to process for a given run.
"""

import json
import os
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
MUST_WATCH_PATH = BASE_DIR / "config" / "must_watch.json"


def load_targets() -> list:
    main = os.environ.get("MAIN", "").strip()
    if main:
        compare_raw = os.environ.get("COMPARE", "")
        compare = [s.strip() for s in compare_raw.split(",") if s.strip()]
        return [{"main": main, "compare": compare, "label": main}]
    return json.loads(MUST_WATCH_PATH.read_text(encoding="utf-8"))
