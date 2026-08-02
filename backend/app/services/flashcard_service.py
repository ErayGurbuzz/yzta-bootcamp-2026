from sqlalchemy.orm import Session

from app.models.document import DocumentChunk
from app.models.flashcard import Flashcard, FlashcardDeck
from app.services.llm_service import LLMService


class FlashcardService:
    def generate(self, *, db: Session, user_id: int, document_id: int, card_count: int) -> list[Flashcard]:
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.page_number.asc(), DocumentChunk.chunk_index.asc())
            .all()
        )
        if not chunks:
            raise ValueError("Dokümanda flashcard üretmek için içerik bulunamadı")

        if len(chunks) > 10:
            step = max(1, len(chunks) // 10)
            chunks = chunks[::step][:10]
        context = "\n\n".join(f"[Sayfa {chunk.page_number}]\n{chunk.text}" for chunk in chunks)
        prompt = f"""
Aşağıdaki ders notlarından {card_count} adet öğretici flashcard üret.
Yalnızca verilen notlardaki bilgileri kullan. Sorular kısa, cevaplar açık ve ezber yerine anlamayı destekleyen nitelikte olsun.
Çıktı sadece geçerli JSON olsun.

{{
  "cards": [
    {{"front": "Kartın soru veya kavram yüzü", "back": "Kısa ve açıklayıcı cevap", "topic": "Kısa konu etiketi", "source_page": 1}}
  ]
}}

DERS NOTLARI:
{context}
""".strip()
        data = LLMService().generate_json(prompt)
        generated = data.get("cards", [])
        if not isinstance(generated, list) or not generated:
            raise ValueError("Yapay zekâ geçerli flashcard üretemedi")

        deck = FlashcardDeck(
            user_id=user_id,
            document_id=document_id,
            title=f"Yapay zekâ çalışma seti - {len(generated[:card_count])} kart",
        )
        db.add(deck)
        db.flush()
        cards = []
        for item in generated[:card_count]:
            front = str(item.get("front", "")).strip()
            back = str(item.get("back", "")).strip()
            if not front or not back:
                continue
            card = Flashcard(
                deck_id=deck.id,
                front=front,
                back=back,
                topic=str(item.get("topic", "Genel")).strip() or "Genel",
                source_page=item.get("source_page"),
            )
            db.add(card)
            cards.append(card)
        if not cards:
            raise ValueError("Kullanılabilir flashcard üretilemedi")
        db.commit()
        for card in cards:
            db.refresh(card)
        return cards
