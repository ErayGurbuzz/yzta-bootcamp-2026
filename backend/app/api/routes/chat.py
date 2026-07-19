from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.chat import ChatMessage
from app.models.document import Document
from app.models.user import User
from app.schemas.chat import ChatAskRequest, ChatAskResponse, ChatHistoryResponse, MultiChatAskRequest
from app.services.embedding_service import MissingGeminiKeyError
from app.services.rag_service import RAGService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask", response_model=ChatAskResponse)
def ask_document(payload: ChatAskRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    document = db.query(Document).filter(Document.id == payload.document_id, Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status != "ready":
        raise HTTPException(status_code=400, detail=f"Document is not ready. Current status: {document.status}")

    try:
        result = RAGService().ask(
            document_ids=[payload.document_id],
            question=payload.question,
            mode=payload.mode,
            top_k=payload.top_k,
        )
    except MissingGeminiKeyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    message = ChatMessage(
        user_id=current_user.id,
        document_id=payload.document_id,
        question=payload.question,
        answer=result["answer"],
        mode=payload.mode,
        source_chunks=result["sources"],
    )
    db.add(message)
    db.commit()
    return result


@router.post("/multi/ask", response_model=ChatAskResponse)
def ask_multiple_documents(payload: MultiChatAskRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    docs = (
        db.query(Document)
        .filter(Document.id.in_(payload.document_ids), Document.user_id == current_user.id, Document.status == "ready")
        .all()
    )
    found_ids = {doc.id for doc in docs}
    if len(found_ids) != len(set(payload.document_ids)):
        raise HTTPException(status_code=404, detail="One or more documents were not found or not ready")

    try:
        result = RAGService().ask(
            document_ids=payload.document_ids,
            question=payload.question,
            mode=payload.mode,
            top_k=payload.top_k,
        )
    except MissingGeminiKeyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    message = ChatMessage(
        user_id=current_user.id,
        document_id=None,
        question=payload.question,
        answer=result["answer"],
        mode=payload.mode,
        source_chunks=result["sources"],
    )
    db.add(message)
    db.commit()
    return result


@router.get("/history", response_model=list[ChatHistoryResponse])
def history(document_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(ChatMessage).filter(ChatMessage.user_id == current_user.id)
    if document_id is not None:
        query = query.filter(ChatMessage.document_id == document_id)
    return query.order_by(ChatMessage.created_at.desc()).limit(30).all()
