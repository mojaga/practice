"""Dynatrace agent identity + query metadata."""
from core.interfaces import ProviderSpec

SPEC = ProviderSpec(
    id="dynatrace",
    name="Dynatrace Agent",
    icon="🟣",
    tagline="Problems, events, SLOs, and metrics from Dynatrace SaaS.",
    query_lang="Dynatrace Environment API v2 path",
    code_lang="text",  # syntax highlight hint for the debug view
    query_gen_prompt=(
        "You are an expert Dynatrace engineer. Convert this question into a single "
        "relative Dynatrace Environment API v2 GET request path that starts with /api/v2/. "
        "Use resources such as /api/v2/problems, /api/v2/events, /api/v2/metrics/query, "
        "/api/v2/entities, /api/v2/slo, and /api/v2/securityProblems. Use Dynatrace selector "
        "syntax (e.g. problemSelector=status(\"open\"), entitySelector=type(\"HOST\"), "
        "metricSelector=builtin:host.cpu.usage), always include a time frame when the resource "
        "supports it (e.g. from=now-24h), and a reasonable page size (e.g. pageSize=100). "
        "Return ONLY the path and query string, for example: "
        "/api/v2/problems?from=now-24h&problemSelector=status(\"open\")&pageSize=100\n\n"
        "IMPORTANT FIELD MAPPINGS — use these exact selectors:\n"
        "- 'devices', 'onboarded', or 'monitored' hosts: /api/v2/entities?entitySelector=type(\"HOST\")&pageSize=100\n"
        "- 'services': entitySelector=type(\"SERVICE\")\n"
        "- 'processes': entitySelector=type(\"PROCESS_GROUP_INSTANCE\")\n"
        "- 'applications': entitySelector=type(\"APPLICATION\")\n"
        "- 'monitored' means an entity exists in /api/v2/entities — Dynatrace only stores monitored entities"
    ),
    connection_note=(
        "Uses the classic Environment API v2 on the `.live.dynatrace.com` domain with an "
        "`Api-Token`. Token needs read scopes such as `problems.read`, `events.read`, "
        "`metrics.read`, and `entities.read`."
    ),
    samples=[
        "What are the active critical problems in the last 24h?",
        "Show hosts with the highest CPU usage.",
        "List any open security problems.",
    ],
    ssl_toggle=False,   # SaaS presents a valid cert; no toggle shown
    ssl_default=True,
)
