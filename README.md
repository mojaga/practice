# ObservIQ - Observability AI Assistant

Ask monitoring questions in plain English. ObservIQ combines Anthropic Claude
with platform tools and optional local runbook retrieval to produce operational
answers backed by platform responses and document references.

| Agent | Platform | Tools |
|---|---|---|
| Dynatrace | Dynatrace SaaS | `query_dynatrace` |
| SolarWinds | SolarWinds Orion (SWIS) | `query_solarwinds` |
| ScienceLogic | ScienceLogic SL1 | `query_sciencelogic`, `onboard_device` |

## Maturity level

| Level | Capability | Status |
|---|---|---|
| L1 | Fixed chatbot pipeline | Implemented; legacy methods retained |
| L2 | RAG assistant | MVP: keyword and optional Chroma semantic retrieval, source excerpts and citation instructions |
| L3 | Tool-using agent | Current active flow, augmented with L2 retrieval |
| L4 | Cross-platform autonomous reasoning | Roadmap |
| L5 | Production controls, evaluations, RBAC and audit | Roadmap |
| L6 | Enterprise multi-agent orchestration | Roadmap |

## Contents

- [Workflow and UI](#workflow-and-ui)
- [Architecture and files](#architecture-and-files)
- [Setup and configuration](#setup-and-configuration)
- [Knowledge retrieval and ingestion](#knowledge-retrieval-and-ingestion)
- [Running the app](#running-the-app)
- [Testing and verification](#testing-and-verification)
- [The provider contract](#the-provider-contract)
- [ScienceLogic write operations](#sciencelogic-write-operations)
- [Adding a platform](#adding-a-platform)
- [Roadmap](#roadmap)

## Workflow and UI

1. Select a monitoring platform and enter a question.
2. Search shared and selected-platform knowledge. The active agent includes the
   previous question in the retrieval query to support follow-up questions.
3. Supply retrieved excerpts, the question, and provider tool definitions to Claude.
4. Execute requested tools through the provider contract and return results to
   Claude. The active loop permits up to ten tool-call iterations.
5. Request a final answer with Summary, Findings, Evidence, and Recommended actions.
   Document-supported claims should cite `[K1]`, `[K2]`, etc. Live tool responses
   establish current platform state; runbooks provide reference guidance.

The Streamlit UI includes:

- Refreshed agent cards, readiness counts, wider chat, and a compact results panel.
- Credential configuration status, platform navigation, SSL settings where supported,
  sample questions, and conversation clearing. Readiness is not a live connection test.
- Live status updates for knowledge lookup, tool execution, and result review.
- Warnings for partial investigations, and clearing of old evidence on new turns.
- Numeric metric cards, nested record tables, CSV downloads, and raw JSON downloads.
  Tables preview up to 500 rows; CSV includes all returned rows. The results panel
  refreshes after a turn completes and represents the latest question.
- Expandable per-answer knowledge excerpts with file names and line ranges, plus
  investigation details containing tool inputs and raw responses.

Conversation history lives in the Streamlit session; saved investigations are not
implemented. Answer sections and citations are requested from the model rather
than enforced. Retrieved references do not prove every passage was used.

## Architecture and files

Agent orchestration and UI routing depend on `core/interfaces.py`, not concrete
provider classes. Each provider owns its prompts, configuration, tool schemas,
and connector. Retrieval uses the provider ID to scope knowledge.

```text
ObservIQ/
  app.py                       Streamlit UI and per-agent session state
  requirements.txt             Base application dependencies
  requirements-rag.txt         Optional Chroma dependencies
  ingest_knowledge.py          Build/update the local semantic index
  core/
    agent.py                   Tool-use loop, progress events, RAG context
    interfaces.py              Provider protocol and metadata
    registry.py                Provider registration and lookup
    config.py                  Project .env loading and Claude settings
    retrieval.py               Scoped loading, BM25 ranking, backend selection
    vector_store.py            Chroma persistence, synchronization and search
  providers/
    dynatrace/
    solarwinds/
    sciencelogic/
  knowledge/
    README.md                  Detailed knowledge setup guide
    shared/
    dynatrace/
    solarwinds/
    sciencelogic/
  utils/formatters.py
  tests/
    test_retrieval.py
    test_vector_store.py
    providers/test_contract.py
```

Retrieval augments the active `ask()` flow and legacy Step C `summarize()` method.
The Chroma ingestion command explicitly lists the four supported knowledge scopes.

## Setup and configuration

Use the established virtual environment at **`C:\ClaudeProjects\.venv`**. All
commands below call its Python directly, so activation is optional. Run commands
from the ObservIQ directory. Docker is not required for local development;
container packaging can follow later.

```powershell
cd "C:\Users\525854\OneDrive - Cognizant\Attachments\Desktop\Cluade Projects\ObservIQ"
& "C:\ClaudeProjects\.venv\Scripts\python.exe" -m pip install -r requirements.txt

# Optional: needed for semantic retrieval
& "C:\ClaudeProjects\.venv\Scripts\python.exe" -m pip install -r requirements-rag.txt
```

Create or edit `ObservIQ/.env`. Configure only the platforms you use:

```dotenv
ANTHROPIC_API_KEY=your-anthropic-api-key
# Optional Claude model override
CLAUDE_MODEL=claude-sonnet-4-6

DYNATRACE_ENV_URL=https://<your-env-id>.live.dynatrace.com
DYNATRACE_API_TOKEN=your-dynatrace-token

SOLARWINDS_SERVER=your-orion-server
SOLARWINDS_USERNAME=your-swis-username
SOLARWINDS_PASSWORD=your-swis-password

SCIENCELOGIC_SERVER=your-tenant.sciencelogic.io
SCIENCELOGIC_USERNAME=your-sl1-username
SCIENCELOGIC_PASSWORD=your-sl1-password

# keyword (default) or chroma; enable chroma after indexing
RAG_BACKEND=keyword
# Optional absolute local database path; outside the OneDrive project
CHROMA_PATH=C:/Users/525854/ObservIQData/chroma
# Semantic cosine-distance cutoff, not a confidence percentage
RAG_MAX_DISTANCE=0.65
```

The app loads `.env` relative to `core/config.py`. The file is gitignored. Keep
secrets out of runbooks and inspect raw responses before sharing debug output or downloads.

### Credential notes per platform

- **Dynatrace** — classic Environment API v2 on the `.live.dynatrace.com` domain
  with an `Api-Token`. The token needs read scopes such as `problems.read`,
  `events.read`, `metrics.read`, `entities.read`. SaaS uses a valid cert (no SSL
  toggle shown).
- **SolarWinds** — connects to the Information Service on **port 17774** using
  SWQL with Basic auth. Orion servers often use a self-signed cert, so **SSL
  verification is off by default**.
- **ScienceLogic** — SL1 SaaS REST API (`/api/...`) with Basic auth. SaaS uses a
  valid TLS certificate, so **SSL verification stays on**. The account needs
  read access for queries and write access for device onboarding.

---


## Knowledge retrieval and ingestion

### Pipeline and backend choice

```text
Reviewed .md/.txt documents
  -> scoped loading and overlapping line chunks
  -> local MiniLM embeddings -> persistent Chroma collection
  -> shared + platform search -> distance cutoff
  -> retrieved excerpts + live monitoring results -> cited Claude answer
```

- **Keyword:** `RAG_BACKEND=keyword` uses local BM25 ranking with no embedding
  dependency. Files are reread each question, so edits and deletions apply immediately.
- **Semantic:** `RAG_BACKEND=chroma` searches an explicitly built local index.
  Rerun ingestion after source changes. These are alternative backends; hybrid
  fusion and reranking are not yet implemented.

### Add your documents

Place reviewed UTF-8 Markdown (`.md`) or plain text (`.txt`) files in
`knowledge/shared/` or the relevant platform folder. Include an owner, review
date, environment applicability, symptoms, diagnostics, and recommended actions.
No operational runbooks are bundled. The README outside these scopes is not indexed.

Unsupported formats, non-UTF-8 files, symlinks, and files over 1 MB are skipped.
PDF/DOCX ingestion is not implemented. Only add documents approved for app users:
platform filtering does not implement document-level or per-user authorization.

### Build or refresh the Chroma index

```powershell
& "C:\ClaudeProjects\.venv\Scripts\python.exe" ingest_knowledge.py
```

The first embedding operation downloads the ONNX **all-MiniLM-L6-v2** model and
requires network access. Embeddings run locally without an embedding API key.
Retrieved excerpts are still sent to the configured Claude API for generation.

Set `RAG_BACKEND=chroma` in `.env`, then restart Streamlit. Rerun ingestion after
adding, editing, or deleting documents. Ingestion upserts chunks and removes
obsolete chunks in all supported scopes. Use one ingestion process at a time,
and avoid editing files during ingestion. Source citations refer to the indexed
version until the next refresh.

### Storage and search behavior

- Default data path: `~/ObservIQData/chroma`; override with `CHROMA_PATH`.
  Keep the index outside the OneDrive-synced project folder.
- Collection: `observiq_minilm_v1`, separate from installation-test vectors.
- Retrieval filters to `shared` plus the selected platform.
- At most four passages are supplied to Claude. Semantic results must pass
  `RAG_MAX_DISTANCE` (default `0.65`); tune against representative questions.
- No relevant hits: proceed with platform evidence without claiming runbook support.
- Chroma failures surface as errors; there is no silent backend switch. Set
  `RAG_BACKEND=keyword` explicitly to return to keyword retrieval.
- Changing the embedding model requires a separate collection and reindexing.

See [knowledge/README.md](knowledge/README.md) for additional guidance.

## Running the app

```powershell
& "C:\ClaudeProjects\.venv\Scripts\python.exe" -m streamlit run app.py
```

Open the URL printed by Streamlit, usually http://localhost:8501, select a
platform, and enter a question.

## Testing and verification

Run the offline retrieval and adapter checks:

```powershell
& "C:\ClaudeProjects\.venv\Scripts\python.exe" -m unittest discover -s tests -p "test_retrieval.py" -v
& "C:\ClaudeProjects\.venv\Scripts\python.exe" -m unittest discover -s tests -p "test_vector_store.py" -v
```

Run the full pytest suite when pytest is installed in that environment:

```powershell
& "C:\ClaudeProjects\.venv\Scripts\python.exe" -m pytest tests/ -q
```

Retrieval tests cover scope isolation, source locations, no-match behavior, file
updates/deletions, unsupported files, and limits. Adapter tests use a fake store
to check synchronization, filtering, and distance cutoffs. Provider contract tests
check required methods and metadata without live platform credentials.

### Latest verification

- Chroma **1.5.9** imported from `C:\ClaudeProjects\.venv\Scripts\python.exe`.
- All **six** keyword retrieval and vector-adapter tests passed.
- A separate real-Chroma smoke check passed persistence, explicit-vector upsert,
  filtered search, metadata lookup, deletion, and cleanup after process exit.
- The smoke check used explicit vectors. MiniLM download, real document embeddings,
  end-to-end ingestion, live Claude answers, and visual UI behavior remain unverified.

On Windows, embedded Chroma may retain file locks until process exit. The smoke
check cleaned its temporary database after the database process had exited.

## The provider contract

Everything hinges on `core/interfaces.py`. A platform is "plugged in" by exposing
one object that satisfies this protocol:

```python
@dataclass(frozen=True)
class ProviderSpec:
    id: str                 # stable key, e.g. "dynatrace"
    name: str               # "Dynatrace Agent"
    icon: str               # "🟣"
    tagline: str            # one-line card description
    query_lang: str         # human name of the query language
    code_lang: str          # st.code syntax-highlight hint
    query_gen_prompt: str   # system prompt teaching Claude this platform's query language
    connection_note: str    # sidebar info text
    samples: list[str]      # example questions / chips
    ssl_toggle: bool = True # whether the UI offers an SSL-verify checkbox
    ssl_default: bool = True

class Provider(Protocol):
    spec: ProviderSpec
    def missing_credentials(self) -> list[str]: ...
    def execute(self, query: str, verify_ssl: bool = True) -> dict | list: ...
    def tools(self) -> list[dict]: ...              # Anthropic tool definitions
    def dispatch_tool(self, name: str, inputs: dict, verify_ssl: bool = True) -> dict | list: ...
```

New capabilities are added here **additively**, so extending one provider never
forces the others to change.

---

## ScienceLogic write operations

ScienceLogic is the first provider with **write operations** alongside read queries.

### Device onboarding

```python
provider.onboard_device(
    ip="10.0.0.1",
    cred_id=1,               # from /api/credential/snmp
    collector_group_id=1,    # from /api/collector_group
    org_id=0,                # 0 = root organisation
)
# → {"status": "created", "location": "/api/device/42", "body": {...}}
```

When you ask *"onboard device 10.0.0.5"* in the chat, Claude automatically:
1. Calls `query_sciencelogic("/api/credential/snmp")` to discover available credentials.
2. Calls `query_sciencelogic("/api/collector_group")` to discover collector groups.
3. Calls `onboard_device(...)` with the discovered IDs.

The SL1 REST API uses URI references for relational fields — the connector
converts integer IDs to `/api/credential/snmp/{id}` form internally.

---


## Adding a platform

1. Create `providers/<platform>/` with `meta.py`, `config.py`, `connector.py`, and
   `__init__.py`. Implement the existing Provider contract.
2. Import and register the provider in `providers/__init__.py`.
3. For Chroma knowledge, create `knowledge/<platform>/` and add its ID to the
   ingestion scopes in `core/vector_store.py`.
4. Run the contract tests and ingest the new platform's documents.

The agent card appears through the registry; agent orchestration and UI routing
need no platform-specific imports.

## Roadmap

- **L2 next:** verify MiniLM download and actual runbook ingestion; evaluate
  retrieval relevance and citation accuracy. Add hybrid search, reranking,
  richer document formats, and document permissions. Tune chunking and thresholds.
- **L4:** cross-platform investigations and controlled autonomous workflows.
- **L5:** evaluations, prompt versioning, cost tracking, audit history, RBAC, CI/CD,
  and deployment packaging after local validation.
- **L6:** specialized agents and ITSM/on-call integration.
- **Vendor MCP:** add provider adapters as needed without changing other providers.

Powered by Anthropic Claude.
