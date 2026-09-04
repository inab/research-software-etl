"""
Single-record similarity over an in-memory embedding cache.

The neighbour maths are pure (`neighbours_for_vector`, `insert_into_neighbours`)
and tested with hand-built unit vectors -- no model. `compute_record_similarity`
is exercised end-to-end against fake repositories with a trivial injected
embedder, so the whole path runs offline.
"""

import numpy as np
import pytest

from application.services.stats_generation.similarity.incremental import (
    compute_record_similarity,
    insert_into_neighbours,
    neighbours_for_vector,
)
from tests.fakes import FakeDatabaseAdapter, fake_repos


# --- pure neighbour maths ----------------------------------------------------------


def test_neighbours_are_ordered_by_score_and_exclude_self():
    ids = ["a", "b", "c"]
    names = ["A", "B", "C"]
    matrix = np.array([[1.0, 0.0], [0.8, 0.6], [0.0, 1.0]], dtype=np.float32)
    target = np.array([1.0, 0.0], dtype=np.float32)

    similar, scores = neighbours_for_vector(
        target, matrix, ids, names, k=2, exclude_id="a"
    )

    # "a" is the closest but is excluded as self; "b" then "c" by descending score.
    assert [s["tool_id"] for s in similar] == ["b", "c"]
    assert similar[0]["score"] == pytest.approx(0.8)
    assert scores.shape == (3,)


def test_insert_into_neighbours_inserts_when_better_than_min():
    similar = [
        {"tool_id": "x1", "tool_name": "X1", "score": 0.1},
        {"tool_id": "x2", "tool_name": "X2", "score": 0.05},
    ]
    updated, changed = insert_into_neighbours(similar, "tgt", "Target", 0.9, k=2)

    assert changed is True
    assert [s["tool_id"] for s in updated] == ["tgt", "x1"]  # trimmed to k, sorted


def test_insert_into_neighbours_is_a_noop_when_not_good_enough():
    similar = [
        {"tool_id": "y1", "tool_name": "Y1", "score": 0.9},
        {"tool_id": "y2", "tool_name": "Y2", "score": 0.85},
    ]
    updated, changed = insert_into_neighbours(similar, "tgt", "Target", 0.8, k=2)

    assert changed is False
    assert updated == similar


def test_insert_into_neighbours_refreshes_a_stale_entry():
    similar = [
        {"tool_id": "tgt", "tool_name": "Target", "score": 0.2},
        {"tool_id": "z1", "tool_name": "Z1", "score": 0.15},
    ]
    updated, changed = insert_into_neighbours(similar, "tgt", "Target", 0.95, k=2)

    assert changed is True
    assert updated[0] == {"tool_id": "tgt", "tool_name": "Target", "score": 0.95}


# --- the service over fake repositories --------------------------------------------


def _seed_embeddings(repos, vectors, model="m"):
    for tool_id, (name, vec) in vectors.items():
        repos.embeddings.upsert_by_tool_id(
            tool_id=tool_id,
            tool_name=name,
            text=name,
            vector=vec,
            model=model,
            version="v1",
        )


TARGET_TOOL = {"_id": "tgt", "data": {"name": "Target"}, "timestamp": "v1"}


def test_compute_record_similarity_writes_neighbours_and_reverse_updates():
    db = FakeDatabaseAdapter()
    repos = fake_repos(db, embeddings=True, similarities=True)

    _seed_embeddings(
        repos,
        {
            "c1": ("C1", [1.0, 0.0]),  # identical direction to the target
            "c2": ("C2", [0.8, 0.6]),
            "c3": ("C3", [0.0, 1.0]),
        },
    )
    # c1's neighbour list has room-to-beat scores; c2's does not.
    repos.similarities.upsert_by_tool_id(
        {
            "tool_id": "c1",
            "tool_name": "C1",
            "similar": [
                {"tool_id": "x1", "tool_name": "X1", "score": 0.1},
                {"tool_id": "x2", "tool_name": "X2", "score": 0.05},
            ],
        }
    )
    repos.similarities.upsert_by_tool_id(
        {
            "tool_id": "c2",
            "tool_name": "C2",
            "similar": [
                {"tool_id": "y1", "tool_name": "Y1", "score": 0.9},
                {"tool_id": "y2", "tool_name": "Y2", "score": 0.85},
            ],
        }
    )

    result = compute_record_similarity(
        repos,
        TARGET_TOOL,
        embed_fn=lambda text: np.array([1.0, 0.0], dtype=np.float32),
        model_name="m",
        k=2,
    )

    assert result == {"neighbours": 2, "reverse_updated": 1}

    target_doc = repos.similarities.find_by_tool_id("tgt")
    assert [s["tool_id"] for s in target_doc["similar"]] == ["c1", "c2"]

    # The target's fresh vector is cached for next time.
    assert repos.embeddings.get("tgt") is not None

    # c1 gained the target (min score beaten); c2 did not.
    c1 = repos.similarities.find_by_tool_id("c1")
    assert c1["similar"][0]["tool_id"] == "tgt"
    c2 = repos.similarities.find_by_tool_id("c2")
    assert all(s["tool_id"] != "tgt" for s in c2["similar"])


def test_reverse_update_can_be_disabled():
    db = FakeDatabaseAdapter()
    repos = fake_repos(db, embeddings=True, similarities=True)
    _seed_embeddings(repos, {"c1": ("C1", [1.0, 0.0])})
    repos.similarities.upsert_by_tool_id(
        {
            "tool_id": "c1",
            "tool_name": "C1",
            "similar": [
                {"tool_id": "x1", "tool_name": "X1", "score": 0.1},
            ],
        }
    )

    result = compute_record_similarity(
        repos,
        TARGET_TOOL,
        embed_fn=lambda text: np.array([1.0, 0.0], dtype=np.float32),
        model_name="m",
        k=2,
        reverse_update=False,
    )

    assert result["reverse_updated"] == 0
    assert all(
        s["tool_id"] != "tgt"
        for s in repos.similarities.find_by_tool_id("c1")["similar"]
    )


def test_empty_cache_is_a_clear_error():
    repos = fake_repos(FakeDatabaseAdapter(), embeddings=True, similarities=True)
    with pytest.raises(RuntimeError, match="cache is empty"):
        compute_record_similarity(
            repos,
            TARGET_TOOL,
            embed_fn=lambda text: np.array([1.0, 0.0], dtype=np.float32),
            model_name="m",
        )


def test_model_mismatch_is_refused():
    db = FakeDatabaseAdapter()
    repos = fake_repos(db, embeddings=True, similarities=True)
    _seed_embeddings(repos, {"c1": ("C1", [1.0, 0.0])}, model="model-a")

    with pytest.raises(ValueError, match="different models"):
        compute_record_similarity(
            repos,
            TARGET_TOOL,
            embed_fn=lambda text: np.array([1.0, 0.0], dtype=np.float32),
            model_name="model-b",
        )
