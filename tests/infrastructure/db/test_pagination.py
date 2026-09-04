"""`fetch_paginated_entries` must stream one cursor and chunk it -- no per-page
`.skip()` (which re-scanned the result set quadratically)."""

from infrastructure.db.mongo.mongo_adapter import MongoDBAdapter


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)
        self.batch_size_arg = None
        self.closed = False

    def batch_size(self, n):
        self.batch_size_arg = n
        return self

    def __iter__(self):
        return iter(self._docs)

    def close(self):
        self.closed = True


class _FakeCollection:
    def __init__(self, docs):
        self._docs = docs
        self.find_calls = []
        self.cursor = None

    def find(self, query, no_cursor_timeout=False):
        self.find_calls.append({"query": query, "no_cursor_timeout": no_cursor_timeout})
        self.cursor = _FakeCursor(self._docs)
        return self.cursor


class _FakeDB:
    def __init__(self, collection):
        self._collection = collection

    def __getitem__(self, name):
        return self._collection


def test_paginates_without_skip_and_closes_cursor(monkeypatch):
    docs = [{"_id": i} for i in range(250)]
    collection = _FakeCollection(docs)
    monkeypatch.setattr(MongoDBAdapter, "db", property(lambda self: _FakeDB(collection)))

    pages = list(MongoDBAdapter().fetch_paginated_entries("c", {"@data_source": "x"}, page_size=100))

    # Chunked 250 into 100/100/50, every doc exactly once, order preserved.
    assert [len(p) for p in pages] == [100, 100, 50]
    assert [d["_id"] for page in pages for d in page] == list(range(250))
    # One cursor for the whole scan -- no per-page skip/limit round-trips.
    assert len(collection.find_calls) == 1
    assert collection.find_calls[0]["no_cursor_timeout"] is True
    assert collection.cursor.closed is True


def test_empty_result_yields_no_pages(monkeypatch):
    collection = _FakeCollection([])
    monkeypatch.setattr(MongoDBAdapter, "db", property(lambda self: _FakeDB(collection)))

    pages = list(MongoDBAdapter().fetch_paginated_entries("c", {}, page_size=100))

    assert pages == []
    assert collection.cursor.closed is True
