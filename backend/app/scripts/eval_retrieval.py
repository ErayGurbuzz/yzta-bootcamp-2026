"""Small retrieval evaluation helper.

Usage inside backend container:
python -m app.scripts.eval_retrieval --document-id 1 --file app/tests/eval_set.sample.json

The script expects GEMINI_API_KEY to be configured because it uses real embeddings.
"""

from __future__ import annotations

import argparse
import json
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--document-id", type=int, required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    data = json.load(open(args.file, encoding="utf-8"))
    embedder = EmbeddingService()
    store = VectorStore()

    hits = 0
    rows = []
    for item in data:
        q = item["question"]
        expected_page = int(item["expected_page"])
        query_vector = embedder.embed_query(q)
        results = store.query(query_embedding=query_vector, document_ids=[args.document_id], top_k=args.top_k)
        pages = [int(r["metadata"].get("page", 0)) for r in results]
        hit = expected_page in pages
        hits += int(hit)
        rows.append({"question": q, "expected_page": expected_page, "retrieved_pages": pages, "hit": hit})

    precision = hits / len(data) if data else 0
    print(json.dumps({"precision_at_k": precision, "rows": rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
