"""Document management endpoints."""

from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.lib.config import settings
from src.lib.database import get_db
from src.lib.logger import get_logger
from src.models.document import ProcessingStatus as DocumentStatus
from src.repositories.document_repo import DocumentRepository

logger = get_logger(__name__)
router = APIRouter()


# Request/Response models
class DocumentCreateRequest(BaseModel):
    """Document creation request."""

    content: str = Field(..., min_length=1, description="Document content")
    source: str = Field(..., min_length=1, description="Document source identifier")
    collection: str = Field(
        default=settings.default_collection,
        description="Collection name",
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Additional metadata (e.g., review_id, product_id)",
    )


class DocumentResponse(BaseModel):
    """Document response model."""

    document_id: str
    source: str
    collection: str
    status: DocumentStatus
    chunk_count: int
    created_at: str
    metadata: Optional[dict] = None

    class Config:
        from_attributes = True


class DocumentDetailResponse(DocumentResponse):
    """Detailed document response with content."""

    content: str
    embedding_job_id: Optional[str] = None


class ChunkResponse(BaseModel):
    """Chunk response model."""

    chunk_id: str
    chunk_index: int
    content: str
    token_count: int
    has_embedding: bool

    class Config:
        from_attributes = True


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    request: DocumentCreateRequest,
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """
    Create a new document and chunk it.

    The document will be:
    1. Stored in the database
    2. Split into chunks
    3. Queued for embedding generation (async)

    Returns the created document with pending status.
    """
    logger.info(f"Creating document from source: {request.source}")

    doc_repo = DocumentRepository(db)

    # Generate document ID
    doc_id = str(uuid4())

    # Create document
    try:
        document = doc_repo.create(
            document_id=doc_id,
            content=request.content,
            source=request.source,
            collection=request.collection,
            metadata=request.metadata or {},
        )

        logger.info(f"Document {doc_id} created with {document.chunk_count} chunks")

        return DocumentResponse(
            document_id=document.id,
            source=document.source,
            collection=document.collection,
            status=document.status,
            chunk_count=document.chunk_count,
            created_at=document.created_at.isoformat(),
            metadata=document.metadata,
        )

    except Exception as e:
        logger.error(f"Failed to create document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document: {str(e)}",
        )


@router.post("/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    collection: str = settings.default_collection,
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """
    Upload a document file (text, CSV, etc.).

    Reads the file content and creates a document.
    Supported formats: .txt, .csv, .md
    """
    logger.info(f"Uploading document: {file.filename}")

    # Validate file type
    allowed_extensions = [".txt", ".csv", ".md"]
    file_ext = None
    for ext in allowed_extensions:
        if file.filename.endswith(ext):
            file_ext = ext
            break

    if not file_ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported. Allowed: {', '.join(allowed_extensions)}",
        )

    # Read file content
    try:
        content = await file.read()
        content_str = content.decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(e)}",
        )

    # Create document
    doc_repo = DocumentRepository(db)
    doc_id = str(uuid4())

    try:
        document = doc_repo.create(
            document_id=doc_id,
            content=content_str,
            source=file.filename,
            collection=collection,
            metadata={"file_type": file_ext, "file_size": len(content)},
        )

        logger.info(f"Document {doc_id} created from upload: {file.filename}")

        return DocumentResponse(
            document_id=document.id,
            source=document.source,
            collection=document.collection,
            status=document.status,
            chunk_count=document.chunk_count,
            created_at=document.created_at.isoformat(),
            metadata=document.metadata,
        )

    except Exception as e:
        logger.error(f"Failed to create document from upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document: {str(e)}",
        )


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    collection: Optional[str] = None,
    status_filter: Optional[DocumentStatus] = None,
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> List[DocumentResponse]:
    """
    List documents with optional filters.

    Supports filtering by collection and status, with pagination.
    """
    doc_repo = DocumentRepository(db)

    # Call list_documents with named parameters
    documents = doc_repo.list_documents(
        collection_name=collection,
        status=status_filter,
        limit=limit,
        offset=offset,
    )

    return [
        DocumentResponse(
            document_id=doc.id,
            source=doc.source,
            collection=doc.collection,
            status=doc.status,
            chunk_count=doc.chunk_count,
            created_at=doc.created_at.isoformat(),
            metadata=doc.metadata,
        )
        for doc in documents
    ]


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: str,
    db: Session = Depends(get_db),
) -> DocumentDetailResponse:
    """
    Get detailed information about a specific document.

    Includes full content and embedding job status.
    """
    doc_repo = DocumentRepository(db)

    document = doc_repo.get_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    return DocumentDetailResponse(
        document_id=document.id,
        source=document.source,
        collection=document.collection,
        status=document.status,
        chunk_count=document.chunk_count,
        content=document.content,
        created_at=document.created_at.isoformat(),
        metadata=document.metadata,
        embedding_job_id=document.embedding_job_id,
    )


@router.get("/documents/{document_id}/chunks", response_model=List[ChunkResponse])
async def get_document_chunks(
    document_id: str,
    db: Session = Depends(get_db),
) -> List[ChunkResponse]:
    """
    Get all chunks for a specific document.

    Returns the text chunks with their embedding status.
    """
    doc_repo = DocumentRepository(db)

    document = doc_repo.get_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    chunks = doc_repo.get_chunks(document_id)

    return [
        ChunkResponse(
            chunk_id=chunk.id,
            chunk_index=chunk.sequence_position,
            content=chunk.text_content,
            token_count=chunk.token_count,
            has_embedding=False,  # TODO: Check Qdrant when vector service is ready
        )
        for chunk in chunks
    ]


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a document and all its chunks.

    This will also remove embeddings from the vector database.
    """
    doc_repo = DocumentRepository(db)

    document = doc_repo.get_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    try:
        # TODO: Delete vectors from Qdrant before deleting from DB
        # This should be implemented when vector service is ready

        doc_repo.delete(document_id)
        logger.info(f"Document {document_id} deleted")

    except Exception as e:
        logger.error(f"Failed to delete document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        )


@router.get("/documents/{document_id}/status")
async def get_document_embedding_status(
    document_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    Get embedding generation status for a document.

    Returns detailed information about embedding progress.
    """
    doc_repo = DocumentRepository(db)

    document = doc_repo.get_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    chunks = doc_repo.get_chunks(document_id)
    # TODO: Query Qdrant to get actual embedding status when vector service is ready
    embedded_chunks = 0

    return {
        "document_id": document_id,
        "status": document.status.value,
        "total_chunks": len(chunks),
        "embedded_chunks": embedded_chunks,
        "progress_percentage": (embedded_chunks / len(chunks) * 100) if chunks else 0,
        "embedding_job_id": None,  # TODO: Get from embedding jobs table
    }
