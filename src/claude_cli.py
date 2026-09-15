"""Call Claude via the Claude Code CLI (`claude -p`), authenticated with
CLAUDE_CODE_OAUTH_TOKEN, instead of the Anthropic Python SDK — billed
against the personal claude.ai subscription's usage instead of separate
pay-as-you-go API credits.

Replaces `client.messages.create(system=..., messages=[...])` calls.
`claude -p` takes one combined prompt on stdin (no separate system/user
roles the way the Messages API has), so system_prompt and user_content
are concatenated. Web search, when requested, goes through Claude Code's
own WebSearch tool rather than Anthropic's hosted web_search tool — there
is no CLI-level hard domain allowlist, so the domain restriction is only
as strong as the instruction in the prompt telling Claude to use it.
"""

import json
import os
import subprocess

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")


class ClaudeCliError(RuntimeError):
    pass


def call_claude(system_prompt: str, user_content: str, allowed_domains: list[str] | None = None) -> str:
    prompt_parts = [system_prompt.strip(), user_content.strip()]
    if allowed_domains:
        domains_text = "、".join(allowed_domains)
        prompt_parts.append(
            "若需要查詢最新消息，只能使用 WebSearch 工具，且務必把 allowed_domains 參數"
            f"設定為以下網域（只能是這些，不要用其他來源）：{domains_text}"
        )
    combined_prompt = "\n\n---\n\n".join(prompt_parts)

    allowed_tools = "WebSearch" if allowed_domains else ""
    cmd = ["claude", "-p", "--output-format", "json", "--model", MODEL]
    if allowed_tools:
        cmd += ["--allowedTools", allowed_tools]

    result = subprocess.run(
        cmd,
        input=combined_prompt,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise ClaudeCliError(
            f"claude -p exited {result.returncode}\nstderr: {result.stderr}\nstdout: {result.stdout}"
        )

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ClaudeCliError(f"claude -p did not return valid JSON: {exc}\nstdout: {result.stdout}") from exc

    if payload.get("is_error"):
        raise ClaudeCliError(f"claude -p reported an error: {payload}")

    text = payload.get("result")
    if not text:
        raise ClaudeCliError(f"claude -p returned no 'result' text: {payload}")
    return text.strip()
