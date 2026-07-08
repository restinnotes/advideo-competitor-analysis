"""JSON 处理工具"""

import json
import re
from pathlib import Path


def strip_markdown_code_block(text: str) -> str:
    pattern = r"^```(?:json)?\s*\n?(.*?)\n?\s*```$"
    match = re.match(pattern, text.strip(), re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def parse_json_with_retry(text: str, max_retries: int = 2, error_log_path: Path | None = None) -> dict:
    cleaned = strip_markdown_code_block(text)
    errors = []

    for attempt in range(max_retries + 1):
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            errors.append({"attempt": attempt + 1, "error": str(e), "text_preview": cleaned[:500]})
            if attempt < max_retries:
                cleaned = _try_fix_json(cleaned)

    if error_log_path:
        error_log_path.parent.mkdir(parents=True, exist_ok=True)
        error_log_path.write_text(
            json.dumps({"errors": errors, "original": text[:5000]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    raise ValueError(f"JSON 解析失败: {errors[-1]['error']}")


def _try_fix_json(text: str) -> str:
    text = text.strip()

    # Find the first { to start
    idx = text.find("{")
    if idx != -1:
        text = text[idx:]

    # Try to find the last complete JSON boundary
    # Look for the last "}" that might close the root object
    last_brace = text.rfind("}")
    if last_brace != -1:
        # Try from the last brace backwards
        candidate = text[: last_brace + 1]
        candidate = _clean_trailing_commas(candidate)
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    # Truncated JSON: try progressively shorter cuts
    # Find last complete key-value pair before truncation
    text = _handle_truncated_json(text)
    text = _clean_trailing_commas(text)

    return text


def _handle_truncated_json(text: str) -> str:
    """Handle truncated JSON by finding the last complete structural boundary."""
    # If the text ends with an unterminated string, cut back to the last comma/brace
    if text.endswith('"') and not text.endswith('\\"'):
        # Check if this is an unterminated string
        # Count unescaped quotes from the end
        i = len(text) - 1
        quote_count = 0
        while i >= 0 and text[i] == '"':
            quote_count += 1
            i -= 1
        if quote_count % 2 == 1:
            # Odd number of trailing quotes means unterminated string
            # Find the last complete value (before the incomplete string)
            # Look for last ",\n" or "]:\n" pattern
            last_complete = text.rfind('",')
            if last_complete == -1:
                last_complete = text.rfind('"\n')
            if last_complete != -1:
                text = text[:last_complete + 1]

    # Now close any open brackets/braces
    opens: list[str] = []
    in_string = False
    escape_next = False

    for ch in text:
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ("{", "["):
            opens.append(ch)
        elif ch == "}":
            if opens and opens[-1] == "{":
                opens.pop()
        elif ch == "]":
            if opens and opens[-1] == "[":
                opens.pop()

    # Close remaining open brackets in reverse order
    closers = {"[": "]", "{": "}"}
    for opener in reversed(opens):
        text += closers.get(opener, "")

    return text


def _clean_trailing_commas(text: str) -> str:
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    return text


def save_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
