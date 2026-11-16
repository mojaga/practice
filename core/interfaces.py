"""Provider contract.

The single abstraction `core` depends on. Every monitoring platform is a
self-contained package under `providers/` that exposes one object satisfying the
`Provider` protocol below. The agent, registry, and UI know *only* this
contract — never a concrete provider — so platforms stay isolated: adding,
changing, or breaking one provider cannot touch another.

New capabilities (vendor MCP servers, custom function tools) are added here
*additively* with defaults, so extending one provider never forces the others
to change.
"""
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ProviderSpec:
    """User-facing identity + query metadata for one platform.

    Everything platform-specific that the UI or agent needs to display or prompt
    with lives here, so no provider-specific strings leak into shared code.
    """
    id: str                       # stable key (e.g. "dynatrace") — used in session_state/registry
    name: str                     # display name, e.g. "Dynatrace Agent"
    icon: str                     # emoji for the card and chat header
    tagline: str                  # one-line card description
    query_lang: str               # human name of the query language (status text)
    code_lang: str                # st.code syntax-highlight hint for the debug view
    query_gen_prompt: str         # system prompt that teaches Claude this platform's query language
    connection_note: str          # sidebar info text describing the connection
    samples: list[str] = field(default_factory=list)  # example questions / chips
    ssl_toggle: bool = True       # whether the UI offers an SSL-verify checkbox
    ssl_default: bool = True      # default SSL-verify value


@runtime_checkable
class Provider(Protocol):
    """What every platform package must implement.

    Implementations hold their own credential config and connector(s); the core
    calls them through this uniform shape with no per-provider branching.
    """
    spec: ProviderSpec

    def missing_credentials(self) -> list[str]:
        """Return the names of .env variables still unset for this provider."""
        ...

    def execute(self, query: str, verify_ssl: bool = True) -> dict | list:
        """Run a generated query against the platform and return raw telemetry."""
        ...

    def tools(self) -> list[dict]:
        """Return Anthropic tool definitions exposed by this provider."""
        ...

    def dispatch_tool(self, name: str, inputs: dict, verify_ssl: bool = True) -> dict | list:
        """Execute a named tool call and return the raw result."""
        ...

    # --- Future additions -----------------------------------------------------
    # def mcp_server(self) -> "McpServerConfig | None": ...
