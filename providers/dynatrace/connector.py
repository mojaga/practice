"""Dynatrace connector — custom REST query functions.

Wraps the Dynatrace classic Environment API v2 as a direct REST client. This is
where custom query functions for Dynatrace live; a vendor MCP server integration
would go beside it in `mcp.py` without affecting other platforms.

"Query language": a relative Environment API v2 request path (e.g. /api/v2/problems?...).
Classic API tokens (dt0c01.*) authenticate here with the `Api-Token` scheme on
the environment's `.live.dynatrace.com` domain. (The Grail DQL query API on the
`.apps.dynatrace.com` platform domain needs OAuth/platform tokens instead.)
"""
import requests

from utils.formatters import http_error_detail


def execute(env_url, token, api_path, verify_ssl=True):
    """GET a relative Environment API v2 path with classic Api-Token auth."""
    base = env_url.strip().rstrip("/")
    # Classic API tokens live on the `.live` domain; translate the platform
    # `.apps` domain automatically so a stale env URL still works.
    base = base.replace(".apps.dynatrace.com", ".live.dynatrace.com")

    path = api_path.strip()
    if not path.startswith("/"):
        path = "/" + path
    endpoint = f"{base}{path}"

    headers = {
        "Authorization": f"Api-Token {token}",
        "Accept": "application/json",
    }

    try:
        response = requests.get(endpoint, headers=headers, verify=verify_ssl, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        return {"error": http_error_detail(e)}
    except Exception as e:
        return {"error": str(e)}
