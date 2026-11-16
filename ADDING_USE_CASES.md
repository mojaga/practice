# Adding New Use Cases to ObservIQ

This guide covers how to add any new operation (read or write) to an existing
platform provider. The pattern is the same every time — 4 steps, all within the
provider's own package. Nothing in `core/` or `app.py` ever changes.

---

## The 4-step pattern

```
Step 1 → providers/<platform>/connector.py      Add the API function
Step 2 → providers/<platform>/__init__.py       Add the wrapper method
Step 3 → providers/<platform>/__init__.py       Add the tool definition to tools()
Step 4 → providers/<platform>/__init__.py       Add the routing case to dispatch_tool()
```

---

## Step 1 — Add the API function to `connector.py`

This is the only place that talks to the platform's REST API.

**Read operation (GET):**
```python
def get_device(server, username, password, device_id, verify_ssl=True):
    host = _base_host(server)
    return _execute_rest(host, username, password,
                         f"/api/device/{device_id}?extended_fetch=1",
                         verify_ssl)
```

**Write operation (POST):**
```python
def create_maintenance_window(server, username, password, name,
                               start_ts, duration_secs, device_ids, verify_ssl=True):
    host = _base_host(server)
    payload = {
        "name":     name,
        "start_time": start_ts,
        "duration": duration_secs,
        "devices":  [f"/api/device/{did}" for did in device_ids],
    }
    return _execute_post(host, username, password, "/api/schedule", payload, verify_ssl)
```

**Rules:**
- Use `_execute_rest()` for GET, `_execute_post()` for POST, `_execute_delete()` for DELETE
- Convert integer IDs to URI references internally (e.g. `/api/device/42`) — callers pass plain ints
- Always return `dict | list` — on failure return `{"error": "..."}`, never raise

---

## Step 2 — Add the wrapper method to the Provider class (`__init__.py`)

The provider class is a thin adapter — it binds credentials to the connector call.
No logic lives here.

```python
def create_maintenance_window(self, name, start_ts, duration_secs,
                               device_ids, verify_ssl=True):
    cfg = self._config()
    return connector.create_maintenance_window(
        cfg.server, cfg.user, cfg.password,
        name, start_ts, duration_secs, device_ids,
        verify_ssl=verify_ssl,
    )
```

---

## Step 3 — Add the tool definition to `tools()`

This is what Claude sees — the name, description, and input schema.
The `description` is the most important field: it tells Claude *when* to use
this tool and what to do first (e.g. look up an ID before calling a write tool).

```python
{
    "name": "create_maintenance_window",
    "description": (
        "Create a maintenance window in ScienceLogic SL1 for one or more devices. "
        "Call query_sciencelogic first to find device IDs (/api/device?extended_fetch=1) "
        "if only a device name or IP is given."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name":          {"type": "string",  "description": "Window name, e.g. 'Patching - web01'"},
            "start_ts":      {"type": "integer", "description": "Start time as Unix timestamp"},
            "duration_secs": {"type": "integer", "description": "Duration in seconds, e.g. 3600 = 1 hour"},
            "device_ids":    {
                "type": "array",
                "items": {"type": "integer"},
                "description": "List of SL1 device IDs to include in the window"
            },
        },
        "required": ["name", "start_ts", "duration_secs", "device_ids"],
    },
}
```

**Input schema types:** `string`, `integer`, `boolean`, `array` (with `items`), `object`

---

## Step 4 — Add the routing case to `dispatch_tool()`

Map the tool name to the wrapper method added in Step 2.

```python
def dispatch_tool(self, name, inputs, verify_ssl=True):
    if name == "query_sciencelogic":
        return self.execute(inputs["query"], verify_ssl=verify_ssl)
    if name == "onboard_device":
        return self.onboard_device(
            inputs["ip"], inputs["cred_id"],
            inputs["collector_group_id"], inputs["org_id"],
            verify_ssl=verify_ssl,
        )
    if name == "create_maintenance_window":          # ← new case
        return self.create_maintenance_window(
            inputs["name"], inputs["start_ts"],
            inputs["duration_secs"], inputs["device_ids"],
            verify_ssl=verify_ssl,
        )
    return {"error": f"Unknown tool: {name}"}
```

---

## After the 4 steps — verify

```powershell
python -m pytest tests/ -q
```

All contract tests must still pass. If a test fails, the provider class is
missing a required method (`tools`, `dispatch_tool`, `execute`, or
`missing_credentials`).

---

## Rules to follow

### When NOT to add a new tool

Read operations don't need a new tool. Claude already calls
`query_sciencelogic` (or `query_dynatrace` / `query_solarwinds`) with any
REST path. Only add a new tool when:

- The operation is a **write** (POST, PUT, DELETE)
- The operation has **structured named inputs** (not just a free-form query string)
- The operation requires **multi-step logic** that Claude should understand explicitly

### Writing good tool descriptions

The description drives Claude's behaviour. A good description answers:

1. **What does this tool do?** (one sentence)
2. **When should Claude use it?** (trigger condition)
3. **What should Claude do first?** (prerequisite — e.g. look up an ID)

Bad:
```
"description": "Creates a maintenance window."
```

Good:
```
"description": (
    "Create a maintenance window in ScienceLogic SL1 for one or more devices. "
    "Call query_sciencelogic first to find device IDs (/api/device?extended_fetch=1) "
    "if only a device name or IP is given."
)
```

### Adding to a different platform

The same 4 steps apply to Dynatrace (`providers/dynatrace/`) and
SolarWinds (`providers/solarwinds/`). Only the connector helpers and API
paths differ. Nothing in `core/` or `app.py` changes.

---

## Quick reference — use cases mapped to steps

| Use case | connector.py function | Tool name |
|---|---|---|
| Create maintenance window | `create_maintenance_window()` | `create_maintenance_window` |
| Delete maintenance window | `delete_maintenance_window(schedule_id)` | `delete_maintenance_window` |
| Acknowledge an event | `acknowledge_event(event_id)` | `acknowledge_event` |
| Close a ticket | `close_ticket(ticket_id)` | `close_ticket` |
| Onboard a device | `onboard_device(ip, ...)` | `onboard_device` |
| List collector groups | reuse `execute()` | `query_sciencelogic` (no new tool needed) |
| Find device by IP | reuse `execute()` | `query_sciencelogic` (no new tool needed) |

---

*Follow this pattern for every new use case — the plugin architecture guarantees
that adding one operation can never affect another platform or break existing tools.*
