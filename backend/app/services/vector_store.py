from __future__ import annotations

import chromadb
from app.config import get_settings


class VectorStore:
    def __init__(self):
        self.settings = get_settings()
        self.client = chromadb.HttpClient(host=self.settings.chroma_host, port=self.settings.chroma_port)
        self.collection = self.client.get_or_create_collection(
            name=self.settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        *,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        if not ids:
            return
        self.collection.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)

    def delete_document(self, document_id: int) -> None:
        self.collection.delete(where={"document_id": document_id})

    def query(self, *, query_embedding: list[float], document_ids: list[int], top_k: int = 5) -> list[dict]:
        if len(document_ids) == 1:
            where = {"document_id": document_ids[0]}
        else:
            where = {"document_id": {"$in": document_ids}}

        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        items: list[dict] = []
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for idx, chunk_id in enumerate(ids):
            metadata = metadatas[idx] or {}
            items.append(
                {
                    "chunk_id": chunk_id,
                    "text": documents[idx],
                    "metadata": metadata,
                    "distance": distances[idx] if idx < len(distances) else None,
                }
            )
        return items
