# Adding a Vendor MCP Server to ObservIQ

This guide covers how to integrate a vendor-provided MCP (Model Context Protocol)
server into an existing provider package. The plugin architecture keeps MCP
integration isolated to one file per platform — nothing in `core/` or `app.py`
ever changes.

---

## How it fits the architecture

**Current (custom connector only):**
```
Claude → tools() → dispatch_tool() → connector.py → Platform REST API
```

**With vendor MCP server:**
```
Claude → tools() → dispatch_tool() ─┬─ connector.py → Platform REST API
                                     └─ mcp.py → Vendor MCP Server → Platform API
```

`tools()` and `dispatch_tool()` are the only integration points. Claude never
knows whether a tool is backed by a custom connector or a vendor MCP server.

---

## Prerequisites

### Uncomment `mcp` in `requirements.txt`

```
mcp>=1.0
```

Then reinstall:

```powershell
pip install -r requirements.txt
```

For Docker, rebuild the image:

```powershell
docker compose up --build
```

---

## Step 1 — Create `providers/<platform>/mcp.py`

This file owns the MCP server connection. It exposes two sync wrappers
(`list_tools_sync` and `call_tool_sync`) so the rest of the codebase stays
synchronous.

```python
# providers/sciencelogic/mcp.py
"""ScienceLogic vendor MCP server integration.

Connects to the official SL1 MCP server process, lists its tools, and
dispatches calls. All async I/O is wrapped in sync helpers so the provider
class stays synchronous.
"""
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Command that launches the vendor MCP server.
# Replace with the actual vendor-provided command and args.
_SERVER_PARAMS = StdioServerParameters(
    command="npx",
    args=["-y", "@sciencelogic/sl1-mcp-server"],
)


async def _list_tools():
    async with stdio_client(_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "input_schema": t.inputSchema,
                }
                for t in result.tools
            ]


async def _call_tool(name, inputs):
    async with stdio_client(_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, inputs)
            return result.content


def list_tools_sync() -> list[dict]:
    """Return Anthropic-format tool definitions from the vendor MCP server."""
    try:
        return asyncio.run(_list_tools())
    except Exception as e:
        return []          # MCP server unavailable — degrade gracefully


def call_tool_sync(name: str, inputs: dict) -> dict:
    """Call a named tool on the vendor MCP server and return the result."""
    try:
        return asyncio.run(_call_tool(name, inputs))
    except Exception as e:
        return {"error": str(e)}
```

**Notes:**
- Replace `@sciencelogic/sl1-mcp-server` with the actual vendor package name.
- SSE transport: replace `stdio_client` with `sse_client` and provide the
  server URL if the vendor uses HTTP/SSE instead of stdio.
- `list_tools_sync` returns `[]` on failure so the provider still loads if the
  MCP server is offline.

---

## Step 2 — Merge MCP tools into `tools()` (`__init__.py`)

Import `mcp` and append vendor tools to the existing custom tools list.

```python
from providers.sciencelogic import connector, mcp   # add mcp import

class ScienceLogicProvider:
    ...

    def tools(self):
        custom_tools = [
            {
                "name": "query_sciencelogic",
                "description": "...",
                "input_schema": { ... },
            },
            {
                "name": "onboard_device",
                "description": "...",
                "input_schema": { ... },
            },
            # add more custom tools here following ADDING_USE_CASES.md
        ]
        vendor_tools = mcp.list_tools_sync()    # tools from the MCP server
        return custom_tools + vendor_tools
```

Custom tools always come first — they take priority if a name collision occurs.

---

## Step 3 — Route MCP tool calls in `dispatch_tool()` (`__init__.py`)

Add a fallthrough at the end of `dispatch_tool()` that forwards unknown tool
names to the MCP server.

```python
def dispatch_tool(self, name, inputs, verify_ssl=True):
    # --- custom tools ---
    if name == "query_sciencelogic":
        return self.execute(inputs["query"], verify_ssl=verify_ssl)
    if name == "onboard_device":
        return self.onboard_device(
            inputs["ip"], inputs["cred_id"],
            inputs["collector_group_id"], inputs["org_id"],
            verify_ssl=verify_ssl,
        )
    # --- vendor MCP tools (fallthrough) ---
    return mcp.call_tool_sync(name, inputs)
```

Any tool name that does not match a custom tool is forwarded to the MCP server.
If the MCP server is offline, `call_tool_sync` returns `{"error": "..."}` which
Claude surfaces in its answer.

---

## Step 4 — Verify

```powershell
python -m pytest tests/ -q
```

All contract tests must still pass. Then run the app and confirm the MCP server
tools appear in the debug expander alongside custom tools.

```powershell
streamlit run app.py
```

---

## Folder structure after integration

```
providers/sciencelogic/
├── connector.py    ← custom REST functions (read + write)
├── mcp.py          ← vendor MCP server connection      ← NEW
├── __init__.py     ← tools() merges both; dispatch_tool() routes to either
├── meta.py         ← identity, system prompt, samples
└── config.py       ← credential schema
```

---

## Transport types

| Transport | When to use | Code change in mcp.py |
|---|---|---|
| **stdio** | Vendor ships a CLI tool / npm package | Use `stdio_client` (default above) |
| **SSE (HTTP)** | Vendor ships a hosted MCP endpoint | Replace `stdio_client` with `sse_client(url)` |

SSE example:
```python
from mcp.client.sse import sse_client

async def _list_tools():
    async with sse_client("https://mcp.vendor.com/sl1") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            ...
```

---

## Rules to follow

| Rule | Detail |
|---|---|
| One `mcp.py` per platform | Never share MCP connections across providers |
| Degrade gracefully | `list_tools_sync` returns `[]` on failure — app still loads |
| Custom tools take priority | Put custom tools first in `tools()` list |
| No changes outside the package | `core/`, `app.py`, and other providers are never touched |
| Verify with pytest | Run tests after every change to confirm the contract is intact |

---

## Adding MCP to Dynatrace or SolarWinds

Exact same 4 steps in their respective packages:

```
providers/dynatrace/mcp.py      ← Dynatrace vendor MCP server
providers/solarwinds/mcp.py     ← SolarWinds vendor MCP server
```

Each platform's MCP integration is fully isolated. A broken MCP server for
one platform cannot affect another.

---

*Related guides:*
- *[ADDING_USE_CASES.md](ADDING_USE_CASES.md) — adding custom read/write operations*
- *[README.md](README.md) — full architecture and maturity roadmap*
