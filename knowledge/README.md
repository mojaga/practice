# Local knowledge for ObservIQ

Place approved UTF-8 Markdown (.md) or plain text (.txt) runbooks in:

- shared/: guidance for all monitoring platforms
- dynatrace/: Dynatrace documentation
- solarwinds/: SolarWinds documentation
- sciencelogic/: ScienceLogic SL1 documentation

This README is outside the search scopes and is not retrieved. No sample
operational advice is bundled: add your own reviewed documents before use.
Include an owner, review date, applicable environment, symptoms, diagnostic
steps, and recommended actions in each runbook. Do not store secrets here.
Documents in these folders are sent as reference excerpts to the configured
Claude API when relevant. Never put documents here that users must not access;
this local MVP does not implement per-user document permissions.

Retrieval uses local BM25 keyword ranking (no embeddings or vector database).
Files are reread for each question, so updates and deletions apply immediately.
Only shared and the selected platform scope are searched. Up to four passages
are included with source paths and line numbers. Files over 1 MB, symlinks,
non-UTF-8 files and unsupported formats are skipped. PDF/DOCX ingestion and
semantic search are not included. Use distinctive service names and terms.

Answers cite [K1], [K2], etc.; expand Knowledge sources for this answer to inspect
excerpts. These are retrieved references, not proof every excerpt was used.
No relevant hits: the agent continues without invented knowledge citations.
Runbooks provide guidance; live API results establish current platform state.


## Chroma semantic retrieval

1. Use the same Python environment as Streamlit:
   `python -m pip install -r requirements-rag.txt`
2. Add reviewed .md/.txt documents to the scope folders above.
3. Build/update the index: `python ingest_knowledge.py`.
4. Set `RAG_BACKEND=chroma` in ObservIQ/.env, then restart the app.

Model: local ONNX all-MiniLM-L6-v2. The first ingestion or query requiring
embeddings downloads model files and requires network access. Documents are
embedded locally; retrieved excerpts still go to Claude for answer generation.
Chroma data defaults to ~/ObservIQData/chroma, outside the OneDrive workspace.
Override with CHROMA_PATH (use an absolute local path).

Rerun ingestion after adding, changing, or removing documents. It synchronizes
all four supported scopes, including removing obsolete chunks; use one ingestion
process at a time. Do not ingest while files are being edited. Source citations
refer to the indexed version until ingestion is rerun. Back up source documents.

Semantic search filters to shared + selected platform. RAG_MAX_DISTANCE defaults
to 0.65 (cosine distance); tune on representative questions, not as a confidence
percentage. No hits below the cutoff means no knowledge context. This version
selects keyword OR semantic search; hybrid ranking and reranking remain future
work. An unavailable Chroma backend surfaces an error rather than silently
switching search behavior. Set RAG_BACKEND=keyword to use the previous retriever.

The default stays keyword until you explicitly enable Chroma. Keep this model's
collection separate from installation-test vectors or future embedding models.
