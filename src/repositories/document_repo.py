"""Repository for document and chunk data access."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.orm import Session

from src.lib.database import Base
from src.lib.exceptions import DatabaseError, NotFoundError
from src.lib.logger import get_logger
from src.models.document import (
    ChunkCreate,
    DocumentCreate,
    ProcessingStatus,
)
from src.models.orm import DocumentORM, ChunkORM

logger = get_logger(__name__)


class DocumentRepository:
    """Repository for document CRUD operations."""

    def __init__(self, db: Session) -> None:
        """
        Initialize repository with database session.

        Args:
            db: SQLAlchemy session
        """
        self.db = db

    def create_document(self, document: DocumentCreate) -> DocumentORM:
        """
        Create a new document record.

        Args:
            document: Document creation data

        Returns:
            Created document

        Raises:
            DatabaseError: If creation fails
        """
        try:
            doc = Document(
                file_name=document.file_name,
                file_format=document.file_format,
                file_size_bytes=document.file_size_bytes,
                collection_name=document.collection_name,
                metadata=document.metadata,
            )

            self.db.add(doc)
            self.db.commit()
            self.db.refresh(doc)

            logger.info(f"Created document: {doc.id}")
            return doc

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create document: {e}")
            raise DatabaseError(f"Document creation failed: {e}")

    def get_document(self, document_id: UUID) -> DocumentORM:
        """
        Get document by ID.

        Args:
            document_id: Document UUID

        Returns:
            Document instance

        Raises:
            NotFoundError: If document not found
            DatabaseError: If query fails
        """
        try:
            stmt = select(DocumentORM).where(Document.id == document_id)
            result = self.db.execute(stmt).scalar_one_or_none()

            if result is None:
                raise NotFoundError(f"Document not found: {document_id}")

            return result

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            raise DatabaseError(f"Document query failed: {e}")

    def list_documents(
        self,
        collection_name: str | None = None,
        status: ProcessingStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DocumentORM]:
        """
        List documents with optional filters.

        Args:
            collection_name: Filter by collection
            status: Filter by processing status
            limit: Maximum results
            offset: Results offset

        Returns:
            List of documents

        Raises:
            DatabaseError: If query fails
        """
        try:
            stmt = select(DocumentORM)

            # Apply filters
            conditions = []
            if collection_name:
                conditions.append(Document.collection_name == collection_name)
            if status:
                conditions.append(Document.status == status)

            if conditions:
                stmt = stmt.where(and_(*conditions))

            # Apply pagination
            stmt = stmt.order_by(Document.uploaded_at.desc()).limit(limit).offset(offset)

            results = self.db.execute(stmt).scalars().all()
            return list(results)

        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            raise DatabaseError(f"Document list query failed: {e}")

    def update_document_status(
        self,
        document_id: UUID,
        status: ProcessingStatus,
        chunk_count: int | None = None,
    ) -> None:
        """
        Update document processing status.

        Args:
            document_id: Document UUID
            status: New processing status
            chunk_count: Optional chunk count to update

        Raises:
            NotFoundError: If document not found
            DatabaseError: If update fails
        """
        try:
            updates: dict[str, Any] = {"status": status}

            if status == ProcessingStatus.COMPLETED:
                updates["processed_at"] = datetime.utcnow()

            if chunk_count is not None:
                updates["chunk_count"] = chunk_count

            stmt = (
                update(Document)
                .where(Document.id == document_id)
                .values(**updates)
            )

            result = self.db.execute(stmt)
            self.db.commit()

            if result.rowcount == 0:
                raise NotFoundError(f"Document not found: {document_id}")

            logger.info(f"Updated document {document_id} status to {status}")

        except NotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update document status: {e}")
            raise DatabaseError(f"Document update failed: {e}")

    def delete_document(self, document_id: UUID) -> None:
        """
        Delete document and its chunks (cascade).

        Args:
            document_id: Document UUID

        Raises:
            NotFoundError: If document not found
            DatabaseError: If deletion fails
        """
        try:
            document = self.get_document(document_id)
            self.db.delete(document)
            self.db.commit()

            logger.info(f"Deleted document: {document_id}")

        except NotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete document: {e}")
            raise DatabaseError(f"Document deletion failed: {e}")

    def create_chunk(self, chunk: ChunkCreate) -> ChunkORM:
        """
        Create a new chunk record.

        Args:
            chunk: Chunk creation data

        Returns:
            Created chunk

        Raises:
            DatabaseError: If creation fails
        """
        try:
            chunk_obj = Chunk(
                document_id=chunk.document_id,
                text_content=chunk.text_content,
                sequence_position=chunk.sequence_position,
                token_count=chunk.token_count,
                char_start_offset=chunk.char_start_offset,
                char_end_offset=chunk.char_end_offset,
                language_code=chunk.language_code,
                metadata=chunk.metadata,
            )

            self.db.add(chunk_obj)
            self.db.commit()
            self.db.refresh(chunk_obj)

            return chunk_obj

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create chunk: {e}")
            raise DatabaseError(f"Chunk creation failed: {e}")

    def create_chunks_bulk(self, chunks: list[ChunkCreate]) -> list[ChunkORM]:
        """
        Create multiple chunks in bulk.

        Args:
            chunks: List of chunk creation data

        Returns:
            List of created chunks

        Raises:
            DatabaseError: If creation fails
        """
        try:
            chunk_objs = [
                Chunk(
                    document_id=chunk.document_id,
                    text_content=chunk.text_content,
                    sequence_position=chunk.sequence_position,
                    token_count=chunk.token_count,
                    char_start_offset=chunk.char_start_offset,
                    char_end_offset=chunk.char_end_offset,
                    language_code=chunk.language_code,
                    metadata=chunk.metadata,
                )
                for chunk in chunks
            ]

            self.db.bulk_save_objects(chunk_objs, return_defaults=True)
            self.db.commit()

            logger.info(f"Created {len(chunk_objs)} chunks in bulk")
            return chunk_objs

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create chunks in bulk: {e}")
            raise DatabaseError(f"Bulk chunk creation failed: {e}")

    def get_chunk(self, chunk_id: UUID) -> ChunkORM:
        """
        Get chunk by ID.

        Args:
            chunk_id: Chunk UUID

        Returns:
            Chunk instance

        Raises:
            NotFoundError: If chunk not found
            DatabaseError: If query fails
        """
        try:
            stmt = select(ChunkORM).where(ChunkORM.id == chunk_id)
            result = self.db.execute(stmt).scalar_one_or_none()

            if result is None:
                raise NotFoundError(f"Chunk not found: {chunk_id}")

            return result

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get chunk {chunk_id}: {e}")
            raise DatabaseError(f"Chunk query failed: {e}")

    def get_chunks_by_document(
        self,
        document_id: UUID,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[ChunkORM]:
        """
        Get all chunks for a document.

        Args:
            document_id: Document UUID
            limit: Maximum results
            offset: Results offset

        Returns:
            List of chunks ordered by sequence position

        Raises:
            DatabaseError: If query fails
        """
        try:
            stmt = (
                select(ChunkORM)
                .where(Chunk.document_id == document_id)
                .order_by(Chunk.sequence_position)
                .limit(limit)
                .offset(offset)
            )

            results = self.db.execute(stmt).scalars().all()
            return list(results)

        except Exception as e:
            logger.error(f"Failed to get chunks for document {document_id}: {e}")
            raise DatabaseError(f"Chunk query failed: {e}")

    def count_chunks_by_document(self, document_id: UUID) -> int:
        """
        Count chunks for a document.

        Args:
            document_id: Document UUID

        Returns:
            Chunk count

        Raises:
            DatabaseError: If query fails
        """
        try:
            stmt = select(func.count()).where(Chunk.document_id == document_id)
            count = self.db.execute(stmt).scalar()
            return count or 0

        except Exception as e:
            logger.error(f"Failed to count chunks for document {document_id}: {e}")
            raise DatabaseError(f"Chunk count query failed: {e}")

    # Helper methods for API layer
    def create(
        self,
        document_id: str,
        content: str,
        source: str,
        collection: str,
        metadata: dict = None,
    ) -> Any:
        """
        Simplified create method for API layer.

        Note: This is a temporary wrapper. The actual implementation should use
        proper document processing with chunking.
        """
        from src.models.document import DocumentCreate, FileFormat

        # For now, create a minimal document
        # TODO: Implement proper document processing pipeline
        doc_create = DocumentCreate(
            file_name=source,
            file_format=FileFormat.TXT,
            file_size_bytes=len(content.encode('utf-8')),
            collection_name=collection,
            metadata=metadata or {},
        )

        # Create a simple namespace object to return
        class SimpleDoc:
            def __init__(self, id, source, collection, status, chunk_count, created_at, metadata):
                self.id = id
                self.source = source
                self.collection = collection
                self.status = status
                self.chunk_count = chunk_count
                self.created_at = created_at
                self.metadata = metadata

        from datetime import datetime
        from src.models.document import ProcessingStatus

        return SimpleDoc(
            id=document_id,
            source=source,
            collection=collection,
            status=ProcessingStatus.PENDING,
            chunk_count=0,
            created_at=datetime.utcnow(),
            metadata=metadata or {},
        )

    def get_by_id(self, document_id: str) -> Any:
        """Get document by ID string (wrapper for get_document)."""
        from uuid import UUID
        return self.get_document(UUID(document_id))

    def get_chunks(self, document_id: str) -> list:
        """Get chunks by document ID string (wrapper for get_chunks_by_document)."""
        from uuid import UUID
        return self.get_chunks_by_document(UUID(document_id))

    def delete(self, document_id: str) -> None:
        """Delete document by ID string (wrapper for delete_document)."""
        from uuid import UUID
        return self.delete_document(UUID(document_id))
