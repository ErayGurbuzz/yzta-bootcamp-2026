from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.config import get_settings
from app.db.session import get_db
from app.models.course import Course
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.schemas.document import DocumentResponse, DocumentStatusResponse
from app.services.document_processor import DocumentProcessor
from app.services.embedding_service import EmbeddingService, MissingGeminiKeyError
from app.services.vector_store import VectorStore

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()


@router.post("/upload", response_model=DocumentResponse, status_code=201)
def upload_document(
    course_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course = db.query(Course).filter(Course.id == course_id, Course.user_id == current_user.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    contents = file.file.read()
    if len(contents) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File size limit is {settings.max_upload_mb} MB")
    if not contents.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid PDF file")

    upload_dir = Path(settings.upload_dir) / str(current_user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid4().hex}.pdf"
    file_path = upload_dir / safe_name
    file_path.write_bytes(contents)

    document = Document(
        user_id=current_user.id,
        course_id=course_id,
        filename=safe_name,
        original_filename=file.filename,
        file_path=str(file_path),
        status="processing",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        _process_document(db, document)
    except MissingGeminiKeyError as exc:
        document.status = "failed"
        document.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        document.status = "failed"
        document.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Document processing failed: {exc}") from exc

    db.refresh(document)
    return document


def _process_document(db: Session, document: Document) -> None:
    processor = DocumentProcessor()
    pages = processor.extract_pages(document.file_path)
    chunks = processor.chunk_pages(pages)
    document.page_count = len(pages)

    db_chunks: list[DocumentChunk] = []
    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict] = []

    for chunk in chunks:
        embedding_id = f"doc-{document.id}-chunk-{chunk.chunk_index}"
        db_chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            page_number=chunk.page_number,
            token_count=chunk.token_count,
            topic_hint=chunk.topic_hint,
            embedding_id=embedding_id,
        )
        db.add(db_chunk)
        db_chunks.append(db_chunk)
        ids.append(embedding_id)
        texts.append(chunk.text)
        metadatas.append(
            {
                "user_id": document.user_id,
                "document_id": document.id,
                "course_id": document.course_id,
                "page": chunk.page_number,
                "chunk_index": chunk.chunk_index,
            }
        )

    embeddings = EmbeddingService().embed_documents(texts)
    VectorStore().add_chunks(ids=ids, texts=texts, embeddings=embeddings, metadatas=metadatas)
    document.status = "ready"
    db.commit()


@router.get("", response_model=list[DocumentResponse])
def list_documents(course_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Document).filter(Document.user_id == current_user.id)
    if course_id is not None:
        query = query.filter(Document.course_id == course_id)
    return query.order_by(Document.created_at.desc()).all()


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def document_status(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).count()
    return DocumentStatusResponse(
        id=document.id,
        status=document.status,
        page_count=document.page_count,
        chunk_count=chunk_count,
        error_message=document.error_message,
    )


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        VectorStore().delete_document(document.id)
    except Exception:
        pass
    try:
        Path(document.file_path).unlink(missing_ok=True)
    except Exception:
        pass
    db.delete(document)
    db.commit()
    return None
