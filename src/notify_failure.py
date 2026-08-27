"""Send a short LINE alert when any step of the committee workflow fails."""

import os

import requests

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def main() -> None:
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    target_ids = [t.strip() for t in os.environ["LINE_PUSH_TARGET_IDS"].split(",") if t.strip()]

    server_url = os.environ.get("GITHUB_SERVER_URL", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    run_url = f"{server_url}/{repo}/actions/runs/{run_id}" if run_id else "(no run URL available)"

    text = f"⚠️ AI 股市投資決策委員會執行失敗，請檢查 GitHub Actions log：\n{run_url}"

    for target_id in target_ids:
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
        print(f"failure alert sent to {target_id}")


if __name__ == "__main__":
    main()
