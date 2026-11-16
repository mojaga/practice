import unittest
from core.retrieval import Passage
from core.vector_store import sync_scope, search


class FakeStore:
    def __init__(self):
        self.items = {}
        self.last_query = None

    def get(self, where, include):
        return {"ids": [k for k, v in self.items.items() if v[1]["scope"] == where["scope"]]}

    def upsert(self, ids, documents, metadatas):
        assert len(ids) == len(set(ids))
        self.items.update({k: (doc, meta) for k, doc, meta in zip(ids, documents, metadatas)})

    def delete(self, ids):
        for key in ids:
            self.items.pop(key)

    def count(self):
        return len(self.items)

    def query(self, **kw):
        self.last_query = kw
        return {"documents": [["guidance", "unrelated"]],
                "metadatas": [[{"source": "shared/a.md", "start_line": 1, "end_line": 2}] * 2],
                "distances": [[0.2, 1.5]]}


class VectorTests(unittest.TestCase):
    def test_sync_updates_deletes_and_scope_isolation(self):
        store = FakeStore()
        old = Passage("shared/a.md", 1, 1, "old")
        new = Passage("shared/a.md", 1, 1, "new")
        other = Passage("dynatrace/b.md", 1, 1, "other")
        sync_scope(store, "shared", [old])
        sync_scope(store, "dynatrace", [other])
        report = sync_scope(store, "shared", [new])
        self.assertEqual(report["removed"], 1)
        sync_scope(store, "shared", [new])
        self.assertEqual(store.count(), 2)
        sync_scope(store, "shared", [])
        self.assertEqual(store.count(), 1)

    def test_search_filters_and_cutoff(self):
        store = FakeStore()
        sync_scope(store, "shared", [Passage("shared/a.md", 1, 2, "guidance")])
        hits = search("question", "dynatrace", store=store)
        self.assertEqual(len(hits), 1)
        self.assertEqual(store.last_query["where"], {"scope": {"$in": ["shared", "dynatrace"]}})
        self.assertEqual(search("", "dynatrace", store=store), [])
        with self.assertRaises(ValueError):
            search("question", "../shared", store=store)
