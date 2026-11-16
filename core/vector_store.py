"""Chroma adapter with explicit local embedding model and provider filtering."""
import hashlib
import os
from pathlib import Path
import re
from core.retrieval import Passage, KNOWLEDGE_ROOT, load_passages

COLLECTION = "observiq_minilm_v1"
MODEL = "all-MiniLM-L6-v2"


def collection():
    try:
        import chromadb
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
    except ImportError as exc:
        raise RuntimeError("Chroma is unavailable. Install requirements-rag.txt using the app's Python environment.") from exc
    path = Path(os.getenv("CHROMA_PATH", str(Path.home() / "ObservIQData" / "chroma"))).expanduser()
    client = chromadb.PersistentClient(path=str(path))
    return client.get_or_create_collection(
        name=COLLECTION, embedding_function=ONNXMiniLM_L6_V2(),
        metadata={"hnsw:space": "cosine", "embedding_model": MODEL})


def sync_scope(store, scope, passages):
    """Upsert a scope before removing obsolete chunks. Rerunning is idempotent."""
    previous = set(store.get(where={"scope": scope}, include=[])["ids"])
    entries = []
    for p in passages:
        identity = f"{p.source}:{p.start_line}:{p.end_line}:{p.text}"
        key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        entries.append((key, p))
    for offset in range(0, len(entries), 64):
        batch = entries[offset:offset + 64]
        store.upsert(ids=[key for key, p in batch], documents=[p.text for key, p in batch],
                     metadatas=[{"scope": scope, "source": p.source, "start_line": p.start_line,
                                 "end_line": p.end_line, "embedding_model": MODEL} for key, p in batch])
    stale = sorted(previous - {key for key, p in entries})
    for offset in range(0, len(stale), 64):
        store.delete(ids=stale[offset:offset + 64])
    return {"scope": scope, "chunks": len(entries), "removed": len(stale)}


def ingest(root=None, store=None):
    root = Path(root) if root is not None else KNOWLEDGE_ROOT
    if not root.is_dir():
        raise ValueError(f"Knowledge directory does not exist: {root}")
    # All configured scopes, including empty folders, are synchronized.
    store = store if store is not None else collection()
    scopes = ("shared", "dynatrace", "solarwinds", "sciencelogic")
    reports = []
    for scope in scopes:
        passages = load_passages(scope, root)
        passages = [p for p in passages if p.source.split("/")[0] == scope]
        reports.append(sync_scope(store, scope, passages))
    return reports


def search(question, provider_id, limit=4, store=None):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", provider_id):
        raise ValueError("Invalid provider scope")
    if not question.strip() or limit <= 0:
        return []
    threshold = float(os.getenv("RAG_MAX_DISTANCE", "0.65"))
    if not 0 <= threshold <= 2:
        raise ValueError("RAG_MAX_DISTANCE must be between 0 and 2")
    store = store if store is not None else collection()
    if not store.count():
        return []
    result = store.query(query_texts=[question], n_results=min(limit, 4, store.count()),
                         where={"scope": {"$in": list(dict.fromkeys(["shared", provider_id]))}},
                         include=["documents", "metadatas", "distances"])
    passages = []
    for text, meta, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
        if distance <= threshold:
            passages.append(Passage(meta["source"], meta["start_line"], meta["end_line"], text, 1 - distance))
    return passages
