"""Collection management endpoints."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.lib.config import settings
from src.lib.database import get_db
from src.lib.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


# Request/Response models
class CollectionCreateRequest(BaseModel):
    """Collection creation request."""

    name: str = Field(..., min_length=1, max_length=100, description="Collection name")
    description: Optional[str] = Field(None, description="Collection description")
    vector_dimensionality: int = Field(
        default=settings.vector_dimension,
        description="Vector dimension (must match embedding model)",
    )
    distance_metric: str = Field(
        default="cosine",
        description="Distance metric for similarity search",
    )
    retention_policy_days: Optional[int] = Field(
        None,
        description="Data retention policy in days (optional)",
    )
    metadata_schema: Optional[dict] = Field(
        None,
        description="JSON schema for collection metadata validation",
    )


class CollectionResponse(BaseModel):
    """Collection response model."""

    name: str
    description: Optional[str]
    vector_dimensionality: int
    distance_metric: str
    document_count: int
    total_vector_count: int
    created_at: str
    last_updated_at: str
    retention_policy_days: Optional[int]
    metadata_schema: Optional[dict]

    class Config:
        from_attributes = True


class CollectionStatsResponse(BaseModel):
    """Collection statistics response."""

    name: str
    document_count: int
    chunk_count: int
    vector_count: int
    total_queries: int
    avg_query_time_ms: Optional[float]
    last_query_at: Optional[str]


@router.get("/collections", response_model=List[CollectionResponse])
async def list_collections(
    db: Session = Depends(get_db),
) -> List[CollectionResponse]:
    """
    List all available collections.

    Returns metadata and statistics for each collection.
    """
    try:
        result = db.execute(
            text("""
                SELECT
                    name,
                    description,
                    vector_dimensionality,
                    distance_metric,
                    document_count,
                    total_vector_count,
                    created_at,
                    last_updated_at,
                    retention_policy_days,
                    metadata_schema
                FROM collections
                ORDER BY created_at DESC
            """)
        )

        collections = []
        for row in result:
            collections.append(
                CollectionResponse(
                    name=row[0],
                    description=row[1],
                    vector_dimensionality=row[2],
                    distance_metric=row[3],
                    document_count=row[4],
                    total_vector_count=row[5],
                    created_at=row[6].isoformat(),
                    last_updated_at=row[7].isoformat(),
                    retention_policy_days=row[8],
                    metadata_schema=row[9],
                )
            )

        return collections

    except Exception as e:
        logger.error(f"Failed to list collections: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collections: {str(e)}",
        )


@router.post("/collections", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    request: CollectionCreateRequest,
    db: Session = Depends(get_db),
) -> CollectionResponse:
    """
    Create a new collection.

    This will create:
    1. A collection entry in PostgreSQL
    2. A corresponding collection in Qdrant vector database

    Note: Collection name must be unique.
    """
    logger.info(f"Creating collection: {request.name}")

    # Check if collection already exists
    try:
        result = db.execute(
            text("SELECT COUNT(*) FROM collections WHERE name = :name"),
            {"name": request.name},
        )
        if result.scalar() > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Collection '{request.name}' already exists",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check collection existence: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify collection uniqueness",
        )

    # Create collection in database
    try:
        db.execute(
            text("""
                INSERT INTO collections (
                    name,
                    description,
                    vector_dimensionality,
                    distance_metric,
                    document_count,
                    total_vector_count,
                    retention_policy_days,
                    metadata_schema
                ) VALUES (
                    :name,
                    :description,
                    :vector_dimensionality,
                    :distance_metric,
                    0,
                    0,
                    :retention_policy_days,
                    :metadata_schema
                )
            """),
            {
                "name": request.name,
                "description": request.description,
                "vector_dimensionality": request.vector_dimensionality,
                "distance_metric": request.distance_metric,
                "retention_policy_days": request.retention_policy_days,
                "metadata_schema": request.metadata_schema,
            },
        )
        db.commit()

        logger.info(f"Collection '{request.name}' created successfully")

        # TODO: Create collection in Qdrant when vector service is ready

        # Get created collection
        result = db.execute(
            text("""
                SELECT
                    name,
                    description,
                    vector_dimensionality,
                    distance_metric,
                    document_count,
                    total_vector_count,
                    created_at,
                    last_updated_at,
                    retention_policy_days,
                    metadata_schema
                FROM collections
                WHERE name = :name
            """),
            {"name": request.name},
        )

        row = result.fetchone()
        return CollectionResponse(
            name=row[0],
            description=row[1],
            vector_dimensionality=row[2],
            distance_metric=row[3],
            document_count=row[4],
            total_vector_count=row[5],
            created_at=row[6].isoformat(),
            last_updated_at=row[7].isoformat(),
            retention_policy_days=row[8],
            metadata_schema=row[9],
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create collection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create collection: {str(e)}",
        )


@router.get("/collections/{collection_name}", response_model=CollectionResponse)
async def get_collection(
    collection_name: str,
    db: Session = Depends(get_db),
) -> CollectionResponse:
    """
    Get detailed information about a specific collection.
    """
    try:
        result = db.execute(
            text("""
                SELECT
                    name,
                    description,
                    vector_dimensionality,
                    distance_metric,
                    document_count,
                    total_vector_count,
                    created_at,
                    last_updated_at,
                    retention_policy_days,
                    metadata_schema
                FROM collections
                WHERE name = :name
            """),
            {"name": collection_name},
        )

        row = result.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found",
            )

        return CollectionResponse(
            name=row[0],
            description=row[1],
            vector_dimensionality=row[2],
            distance_metric=row[3],
            document_count=row[4],
            total_vector_count=row[5],
            created_at=row[6].isoformat(),
            last_updated_at=row[7].isoformat(),
            retention_policy_days=row[8],
            metadata_schema=row[9],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get collection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get collection: {str(e)}",
        )


@router.get("/collections/{collection_name}/stats", response_model=CollectionStatsResponse)
async def get_collection_stats(
    collection_name: str,
    db: Session = Depends(get_db),
) -> CollectionStatsResponse:
    """
    Get detailed statistics for a collection.

    Includes:
    - Document and chunk counts
    - Query statistics
    - Performance metrics
    """
    # Verify collection exists
    try:
        result = db.execute(
            text("SELECT COUNT(*) FROM collections WHERE name = :name"),
            {"name": collection_name},
        )
        if result.scalar() == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify collection",
        )

    try:
        # Get document count
        result = db.execute(
            text("SELECT COUNT(*) FROM documents WHERE collection_name = :collection"),
            {"collection": collection_name},
        )
        document_count = result.scalar()

        # Get chunk count
        result = db.execute(
            text("""
                SELECT COUNT(c.*)
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE d.collection_name = :collection
            """),
            {"collection": collection_name},
        )
        chunk_count = result.scalar()

        # Get vector count (same as chunk count for now)
        # TODO: Query Qdrant to get actual vector count when vector service is ready
        vector_count = chunk_count

        # Get query statistics
        result = db.execute(
            text("SELECT COUNT(*) FROM queries WHERE collection_name = :collection"),
            {"collection": collection_name},
        )
        total_queries = result.scalar()

        # Get average query time (if available)
        # TODO: Implement query time tracking in query processing
        avg_query_time_ms = None

        # Get last query time
        result = db.execute(
            text("""
                SELECT submitted_at
                FROM queries
                WHERE collection_name = :collection
                ORDER BY submitted_at DESC
                LIMIT 1
            """),
            {"collection": collection_name},
        )
        last_query_row = result.fetchone()
        last_query_at = last_query_row[0].isoformat() if last_query_row else None

        return CollectionStatsResponse(
            name=collection_name,
            document_count=document_count,
            chunk_count=chunk_count,
            vector_count=vector_count,
            total_queries=total_queries,
            avg_query_time_ms=avg_query_time_ms,
            last_query_at=last_query_at,
        )

    except Exception as e:
        logger.error(f"Failed to get collection stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get collection stats: {str(e)}",
        )


@router.delete("/collections/{collection_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_name: str,
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a collection and all its documents.

    This will cascade delete:
    - All documents in the collection
    - All chunks from those documents
    - All embeddings from Qdrant

    Warning: This operation cannot be undone.
    """
    # Prevent deletion of default collection
    if collection_name == settings.default_collection:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot delete default collection '{settings.default_collection}'",
        )

    # Verify collection exists
    try:
        result = db.execute(
            text("SELECT COUNT(*) FROM collections WHERE name = :name"),
            {"name": collection_name},
        )
        if result.scalar() == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify collection",
        )

    try:
        # TODO: Delete collection from Qdrant

        # Delete all documents in the collection (cascades to chunks)
        db.execute(
            text("DELETE FROM documents WHERE collection_name = :collection"),
            {"collection": collection_name},
        )

        # Delete collection
        db.execute(
            text("DELETE FROM collections WHERE name = :name"),
            {"name": collection_name},
        )

        db.commit()

        logger.info(f"Collection '{collection_name}' deleted successfully")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete collection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete collection: {str(e)}",
        )
