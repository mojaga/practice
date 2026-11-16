"""Run from the project environment: python ingest_knowledge.py"""
from core.vector_store import ingest

if __name__ == "__main__":
    for result in ingest():
        print(f"{result['scope']}: {result['chunks']} indexed chunks, {result['removed']} obsolete chunks removed")
    print("Index ready. Set RAG_BACKEND=chroma before starting ObservIQ.")
