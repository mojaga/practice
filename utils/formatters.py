"""UI / text formatting helpers."""


def extract_query(raw_text):
    """Pull a clean query string out of Claude's response.

    Strips markdown code fences (```dql / ```sql / ```) and stray backticks
    that would otherwise break the downstream query.
    """
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop the opening fence (e.g. ``` or ```sql)
        lines = lines[1:]
        # Drop the closing fence if present
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.replace("`", "").strip()


def http_error_detail(exc):
    """Build a readable message from a requests HTTPError, including the body."""
    detail = ""
    try:
        detail = exc.response.text
    except Exception:
        pass
    status = getattr(getattr(exc, "response", None), "status_code", "?")
    return f"HTTP {status}: {detail or str(exc)}"
