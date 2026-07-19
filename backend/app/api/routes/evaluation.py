from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.services.embedding_service import EmbeddingService, MissingGeminiKeyError
from app.services.vector_store import VectorStore

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/retrieval-check")
def retrieval_check(
    document_id: int,
    question: str,
    expected_page: int,
    top_k: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        query_vector = EmbeddingService().embed_query(question)
        results = VectorStore().query(query_embedding=query_vector, document_ids=[document_id], top_k=top_k)
    except MissingGeminiKeyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    pages = [int(r["metadata"].get("page", 0)) for r in results]
    return {
        "question": question,
        "expected_page": expected_page,
        "retrieved_pages": pages,
        "hit": expected_page in pages,
        "precision_at_k": 1.0 if expected_page in pages else 0.0,
    }
