from dataclasses import dataclass
from pathlib import Path
import re
import fitz  # PyMuPDF


@dataclass
class PageText:
    page_number: int
    text: str


@dataclass
class Chunk:
    text: str
    page_number: int
    chunk_index: int
    token_count: int
    topic_hint: str | None = None


class DocumentProcessor:
    def extract_pages(self, file_path: str) -> list[PageText]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        pages: list[PageText] = []
        with fitz.open(file_path) as doc:
            for idx, page in enumerate(doc, start=1):
                text = page.get_text("text") or ""
                clean_text = self.clean_text(text)
                if clean_text:
                    pages.append(PageText(page_number=idx, text=clean_text))
        return pages

    def clean_text(self, text: str) -> str:
        text = text.replace("\x00", " ")
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"Page\s+\d+", " ", text, flags=re.IGNORECASE)
        return text.strip()

    def chunk_pages(self, pages: list[PageText], chunk_size: int = 600, overlap: int = 120) -> list[Chunk]:
        if chunk_size <= overlap:
            raise ValueError("chunk_size must be greater than overlap")

        chunks: list[Chunk] = []
        index = 0
        for page in pages:
            words = page.text.split()
            if not words:
                continue
            start = 0
            while start < len(words):
                end = min(start + chunk_size, len(words))
                chunk_words = words[start:end]
                chunk_text = " ".join(chunk_words)
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        page_number=page.page_number,
                        chunk_index=index,
                        token_count=len(chunk_words),
                        topic_hint=self.topic_hint(chunk_text),
                    )
                )
                index += 1
                if end == len(words):
                    break
                start = end - overlap
        return chunks

    def topic_hint(self, text: str) -> str | None:
        # Lightweight, non-AI hint used only as metadata. Quiz topic comes from LLM structured output.
        sentences = re.split(r"[.!?]", text)
        first = next((s.strip() for s in sentences if len(s.strip()) > 20), None)
        if not first:
            return None
        return first[:80]
