"""Provider packages.

Each subpackage is a self-contained platform integration (identity, credential
schema, connector, and — later — vendor MCP server + custom tools) that
satisfies the `core.interfaces.Provider` contract. Platforms are isolated: one
package cannot import or break another.

Registration is explicit and lives here so the full set of active agents is
visible in one place. Adding a platform = create a package + add two lines
below. Nothing in `core/` or `app.py` changes.
"""
from core.registry import register

from providers.dynatrace import PROVIDER as dynatrace
from providers.solarwinds import PROVIDER as solarwinds
from providers.sciencelogic import PROVIDER as sciencelogic

register(dynatrace)
register(solarwinds)
register(sciencelogic)
