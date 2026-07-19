from __future__ import annotations

from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.vector_store import VectorStore


class RAGService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        self.llm_service = LLMService()

    def ask(self, *, document_ids: list[int], question: str, mode: str = "default", top_k: int = 5) -> dict:
        query_vector = self.embedding_service.embed_query(question)
        retrieved = self.vector_store.query(query_embedding=query_vector, document_ids=document_ids, top_k=top_k)

        if not retrieved:
            return {
                "answer": "Bu dokümanlarda soruyu yanıtlamak için yeterli içerik bulunamadı.",
                "sources": [],
            }

        context_lines = []
        sources = []
        for item in retrieved:
            metadata = item["metadata"]
            page = int(metadata.get("page", 0))
            doc_id = int(metadata.get("document_id", 0))
            text = item["text"]
            context_lines.append(f"[Kaynak: Doküman {doc_id}, Sayfa {page}, Chunk {item['chunk_id']}]\n{text}")
            sources.append(
                {
                    "document_id": doc_id,
                    "chunk_id": item["chunk_id"],
                    "page": page,
                    "text_preview": text[:240],
                    "distance": item.get("distance"),
                }
            )

        prompt = self._build_prompt("\n\n".join(context_lines), question, mode)
        answer = self.llm_service.generate_text(prompt)
        return {"answer": answer, "sources": sources}

    def _build_prompt(self, context: str, question: str, mode: str) -> str:
        mode_instruction = {
            "default": "Yanıtı açık, kısa ve belgeye bağlı şekilde ver.",
            "simple": "Konuyu daha basit, lise öğrencisinin anlayacağı şekilde anlat. Gereksiz teknik jargon kullanma.",
            "examples": "Yanıtta kısa bir açıklama ve en az bir somut örnek ver.",
        }.get(mode, "Yanıtı açık, kısa ve belgeye bağlı şekilde ver.")

        return f"""
Sen StudyMate adlı öğrenci soru asistanısın.
SADECE aşağıdaki bağlamdan yararlanarak cevap ver.
Bağlamda cevap yoksa açıkça: "Bu bilgi yüklenen dokümanda bulunmuyor." de.
Halüsinasyon yapma, dış bilgi ekleme.
Cevabın sonunda kullandığın sayfaları "Kaynak: Sayfa X, Sayfa Y" formatında belirt.

Yanıt modu: {mode_instruction}

BAĞLAM:
{context}

SORU:
{question}

YANIT:
""".strip()
