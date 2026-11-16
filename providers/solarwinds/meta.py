"""SolarWinds agent identity + query metadata."""
from core.interfaces import ProviderSpec

SPEC = ProviderSpec(
    id="solarwinds",
    name="SolarWinds Agent",
    icon="🟠",
    tagline="Nodes, interfaces, and active alerts from Orion via SWQL.",
    query_lang="SWQL (SolarWinds Query Language)",
    code_lang="sql",
    query_gen_prompt=(
        "You are an expert SolarWinds Orion engineer. Convert this question into a valid "
        "SWQL query. SWQL is SQL-like: use SELECT ... FROM Orion.<Entity> with Orion schema "
        "tables such as Orion.Nodes, Orion.NPM.Interfaces, Orion.APM.Application, and "
        "Orion.AlertActive. Always include a reasonable TOP N (e.g. TOP 100) to bound results.\n\n"
        "IMPORTANT FIELD MAPPINGS — use these exact values:\n"
        "- 'onboarded', 'managed', or 'active' devices/nodes: SELECT TOP 100 NodeID, Caption, IPAddress, Status, Vendor FROM Orion.Nodes WHERE Unmanaged=False\n"
        "- 'unmanaged' nodes: WHERE Unmanaged=True\n"
        "- node Status values: 1=Up, 2=Down, 3=Warning, 9=Unknown\n"
        "- 'down' nodes: WHERE Status=2\n"
        "- active alerts: SELECT TOP 100 AlertID, AlertDefID, NodeID FROM Orion.AlertActive"
    ),
    connection_note=(
        "Connects to the SolarWinds Information Service on port 17774 using SWQL. Orion "
        "servers often use a self-signed cert, so SSL verification is off by default."
    ),
    samples=[
        "Which nodes are currently down?",
        "Show the top 10 interfaces by traffic.",
        "List all active alerts.",
    ],
    ssl_toggle=True,
    ssl_default=False,  # Orion often uses a self-signed cert
)
