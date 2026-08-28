"""Parse the committee narrative's ##BASIC##/##STRATEGY##/##RISK##/##NEWS##
delimiter format into structured data (mirrors ai-stock-weekly-report-bot's
generate_report.py parser), so the numbers computed in lib.py stay separate
from the model's prose and a Flex Message card can be built from both.
"""

import re

SECTION_RE = re.compile(r"^##([A-Z]+)##\s*$", re.MULTILINE)


def parse_sections(text: str) -> dict | None:
    matches = list(SECTION_RE.finditer(text))
    if not matches:
        return None

    raw = {}
    for i, m in enumerate(matches):
        name = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw[name] = text[start:end].strip()

    if "BASIC" not in raw:
        return None

    news = []
    for line in raw.get("NEWS", "").splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 2 and parts[1].startswith("http"):
            news.append({"title": parts[0], "url": parts[1]})

    return {
        "basic": raw.get("BASIC", "").strip(),
        "strategy": raw.get("STRATEGY", "").strip(),
        "risk_note": raw.get("RISK", "").strip(),
        "news": news,
    }
