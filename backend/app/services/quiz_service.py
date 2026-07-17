from __future__ import annotations

from collections import defaultdict
from sqlalchemy.orm import Session
from app.models.document import DocumentChunk
from app.models.quiz import Quiz, QuizQuestion, QuizAttempt, QuizAnswer
from app.services.llm_service import LLMService


class QuizService:
    def __init__(self):
        self.llm_service = LLMService()

    def generate_quiz(
        self,
        *,
        db: Session,
        user_id: int,
        document_id: int,
        question_count: int,
        difficulty: str,
        question_type: str,
    ) -> Quiz:
        chunks = self._select_chunks(db, document_id, max_chunks=8)
        if not chunks:
            raise ValueError("Document has no chunks. Upload/process the PDF first.")

        context = "\n\n".join(
            f"[Sayfa {c.page_number}, Chunk {c.chunk_index}]\n{c.text}" for c in chunks
        )
        prompt = self._quiz_prompt(context, question_count, difficulty, question_type)
        data = self.llm_service.generate_json(prompt)
        questions = data.get("questions", [])
        if not isinstance(questions, list) or not questions:
            raise ValueError("LLM did not return valid quiz questions")

        quiz = Quiz(
            user_id=user_id,
            document_id=document_id,
            title=f"StudyMate Quiz - {difficulty}",
            difficulty=difficulty,
            question_count=min(question_count, len(questions)),
        )
        db.add(quiz)
        db.flush()

        for q in questions[:question_count]:
            options = q.get("options") or []
            if isinstance(options, dict):
                options = [f"{key}) {value}" for key, value in options.items()]
            if question_type == "mcq" and len(options) < 2:
                continue
            db.add(
                QuizQuestion(
                    quiz_id=quiz.id,
                    question_text=str(q.get("question", "")).strip(),
                    question_type=str(q.get("type", question_type)).strip() or question_type,
                    options=options,
                    correct_answer=str(q.get("correct_answer", "")).strip(),
                    explanation=str(q.get("explanation", "")).strip(),
                    topic=str(q.get("topic", "Genel")).strip() or "Genel",
                    source_page=q.get("source_page"),
                )
            )
        db.commit()
        db.refresh(quiz)
        return quiz

    def submit_quiz(self, *, db: Session, user_id: int, quiz: Quiz, submitted: dict[int, str]) -> dict:
        questions = quiz.questions
        score = 0
        topic_stats = defaultdict(lambda: {"correct": 0, "total": 0, "pages": set()})
        answer_results = []

        attempt = QuizAttempt(
            quiz_id=quiz.id,
            user_id=user_id,
            total_questions=len(questions),
        )
        db.add(attempt)
        db.flush()

        for question in questions:
            user_answer = (submitted.get(question.id) or "").strip()
            is_correct = self._normalize(user_answer) == self._normalize(question.correct_answer)
            if is_correct:
                score += 1

            topic_stats[question.topic]["total"] += 1
            if is_correct:
                topic_stats[question.topic]["correct"] += 1
            if question.source_page:
                topic_stats[question.topic]["pages"].add(question.source_page)

            qa = QuizAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                user_answer=user_answer,
                is_correct=is_correct,
                correct_answer=question.correct_answer,
                explanation=question.explanation,
                topic=question.topic,
                source_page=question.source_page,
            )
            db.add(qa)
            answer_results.append(
                {
                    "question_id": question.id,
                    "question_text": question.question_text,
                    "user_answer": user_answer,
                    "correct_answer": question.correct_answer,
                    "is_correct": is_correct,
                    "explanation": question.explanation,
                    "topic": question.topic,
                    "source_page": question.source_page,
                }
            )

        percentage = round((score / len(questions)) * 100, 2) if questions else 0.0
        weak_topic = self._find_weak_topic(topic_stats)
        recommendation = self._recommendation(weak_topic, topic_stats) if weak_topic else "Tüm konularda iyi görünüyorsun. Tekrar için kısa bir genel quiz çözebilirsin."

        attempt.score = score
        attempt.percentage = percentage
        attempt.weak_topic = weak_topic
        attempt.recommendation = recommendation
        db.commit()
        db.refresh(attempt)

        return {
            "attempt_id": attempt.id,
            "score": score,
            "total_questions": len(questions),
            "percentage": percentage,
            "weak_topic": weak_topic,
            "recommendation": recommendation,
            "answers": answer_results,
        }

    def _select_chunks(self, db: Session, document_id: int, max_chunks: int) -> list[DocumentChunk]:
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.page_number.asc(), DocumentChunk.chunk_index.asc())
            .all()
        )
        if len(chunks) <= max_chunks:
            return chunks
        step = max(1, len(chunks) // max_chunks)
        selected = chunks[::step][:max_chunks]
        return selected

    def _quiz_prompt(self, context: str, question_count: int, difficulty: str, question_type: str) -> str:
        return f"""
Aşağıdaki ders notlarına dayanarak {question_count} adet {difficulty} seviye quiz sorusu üret.
Sadece verilen bağlamdan soru üret. Bağlamda olmayan bilgi ekleme.
Çıktı SADECE geçerli JSON olsun. Markdown kullanma.

JSON şeması:
{{
  "questions": [
    {{
      "question": "Soru metni",
      "type": "mcq",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct_answer": "A",
      "explanation": "Doğru cevabın kısa açıklaması",
      "topic": "Konu etiketi",
      "source_page": 3
    }}
  ]
}}

Kurallar:
- type değeri "{question_type}" olsun.
- correct_answer sadece seçenek harfi veya true/false olsun.
- explanation öğrencinin neden yanlış yaptığını anlayacağı kadar açık olsun.
- topic alanı Learning Analytics için kısa ve anlamlı olsun.
- source_page mutlaka bağlamdaki sayfa numaralarından biri olsun.

BAĞLAM:
{context}
""".strip()

    def _normalize(self, value: str) -> str:
        value = value.strip().upper()
        if ")" in value:
            value = value.split(")", 1)[0]
        return value

    def _find_weak_topic(self, topic_stats: dict) -> str | None:
        weakest = None
        weakest_rate = 1.1
        for topic, stats in topic_stats.items():
            total = stats["total"]
            if total == 0:
                continue
            rate = stats["correct"] / total
            if rate < weakest_rate:
                weakest_rate = rate
                weakest = topic
        return weakest if weakest_rate < 1 else None

    def _recommendation(self, weak_topic: str, topic_stats: dict) -> str:
        pages = sorted(topic_stats[weak_topic]["pages"])
        page_text = ", ".join(str(p) for p in pages) if pages else "ilgili kaynak sayfaları"
        return (
            f"En çok zorlandığın konu: {weak_topic}. "
            f"Önce {page_text} sayfalarını tekrar et. "
            f"Ardından aynı konudan 5 soruluk kısa bir tekrar quiz'i çöz."
        )
