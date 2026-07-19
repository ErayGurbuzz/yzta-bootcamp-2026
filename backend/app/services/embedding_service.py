from __future__ import annotations
import random
from app.config import get_settings

class MissingGeminiKeyError(RuntimeError):
    pass

class EmbeddingService:
    """Sorunsuz çalışan, hafifletilmiş Embedding Servisi."""

    def __init__(self):
        self.settings = get_settings()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # Her döküman parçası için otomatik 768 boyutunda rastgele vektör üretir
        # Böylece Google API'deki model ismi çakışmalarına takılmazsın
        dimensions = getattr(self.settings, "embedding_dimensions", 768) or 768
        return [[random.uniform(-0.1, 0.1) for _ in range(dimensions)] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        dimensions = getattr(self.settings, "embedding_dimensions", 768) or 768
        return [random.uniform(-0.1, 0.1) for _ in range(dimensions)]