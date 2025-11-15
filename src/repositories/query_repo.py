"""Repository for query, answer, and query result data access."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from src.lib.exceptions import DatabaseError, NotFoundError
from src.lib.logger import get_logger
from src.models.orm import QueryORM, AnswerORM, QueryResultORM
from src.models.query import (
    ProcessingStatus,
    ValidationStatus,
    # Pydantic models for input/output
    Query as QueryPydantic,
    Answer as AnswerPydantic,
    QueryResult as QueryResultPydantic,
    QueryCreate,
)

logger = get_logger(__name__)


class QueryRepository:
    """Repository for query, answer, and query result operations."""

    def __init__(self, db: Session) -> None:
        """
        Initialize repository with database session.

        Args:
            db: SQLAlchemy session
        """
        self.db = db

    # Query operations

    def create_query(self, query: QueryCreate) -> QueryORM:
        """
        Create a new query record.

        Args:
            query: Query creation data

        Returns:
            Created query

        Raises:
            DatabaseError: If creation fails
        """
        try:
            from datetime import datetime

            query_obj = QueryORM(
                query_text=query.query_text,
                user_id=query.user_id,
                collection_name=query.collection_name,
                language_code='pt-BR',
                status=ProcessingStatus.PENDING,
                submitted_at=datetime.utcnow(),
            )

            self.db.add(query_obj)
            self.db.commit()
            self.db.refresh(query_obj)

            logger.info(f"Created query: {query_obj.id}")
            return query_obj

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create query: {e}")
            raise DatabaseError(f"Query creation failed: {e}")

    def get_query(self, query_id: UUID) -> QueryORM:
        """
        Get query by ID.

        Args:
            query_id: Query UUID

        Returns:
            Query instance

        Raises:
            NotFoundError: If query not found
            DatabaseError: If query fails
        """
        try:
            stmt = select(QueryORM).where(QueryORM.id == query_id)
            result = self.db.execute(stmt).scalar_one_or_none()

            if result is None:
                raise NotFoundError(f"Query not found: {query_id}")

            return result

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get query {query_id}: {e}")
            raise DatabaseError(f"Query fetch failed: {e}")

    def update_query_status(
        self,
        query_id: UUID,
        status: ProcessingStatus,
        worker_id: str | None = None,
    ) -> None:
        """
        Update query processing status.

        Args:
            query_id: Query UUID
            status: New processing status
            worker_id: Optional worker identifier

        Raises:
            NotFoundError: If query not found
            DatabaseError: If update fails
        """
        try:
            query = self.get_query(query_id)
            query.status = status

            if worker_id:
                query.worker_id = worker_id

            self.db.commit()
            logger.info(f"Updated query {query_id} status to {status}")

        except NotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update query status: {e}")
            raise DatabaseError(f"Query update failed: {e}")

    def list_queries(
        self,
        user_id: str | None = None,
        status: ProcessingStatus | None = None,
        collection_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[QueryORM]:
        """
        List queries with optional filters.

        Args:
            user_id: Filter by user
            status: Filter by status
            collection_name: Filter by collection
            limit: Maximum results
            offset: Results offset

        Returns:
            List of queries

        Raises:
            DatabaseError: If query fails
        """
        try:
            stmt = select(QueryORM)

            # Apply filters
            conditions = []
            if user_id:
                conditions.append(QueryORM.user_id == user_id)
            if status:
                conditions.append(QueryORM.status == status)
            if collection_name:
                conditions.append(QueryORM.collection_name == collection_name)

            if conditions:
                stmt = stmt.where(and_(*conditions))

            # Apply pagination
            stmt = stmt.order_by(QueryORM.submitted_at.desc()).limit(limit).offset(offset)

            results = self.db.execute(stmt).scalars().all()
            return list(results)

        except Exception as e:
            logger.error(f"Failed to list queries: {e}")
            raise DatabaseError(f"Query list failed: {e}")

    # Answer operations

    def create_answer(self, answer: AnswerORM) -> AnswerORM:
        """
        Create a new answer record.

        Args:
            answer: AnswerORM instance

        Returns:
            Created answer

        Raises:
            DatabaseError: If creation fails
        """
        try:
            self.db.add(answer)
            self.db.commit()
            self.db.refresh(answer)

            logger.info(f"Created answer: {answer.id} for query: {answer.query_id}")
            return answer

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create answer: {e}")
            raise DatabaseError(f"Answer creation failed: {e}")

    def get_answer(self, answer_id: UUID) -> AnswerORM:
        """
        Get answer by ID.

        Args:
            answer_id: Answer UUID

        Returns:
            Answer instance

        Raises:
            NotFoundError: If answer not found
            DatabaseError: If query fails
        """
        try:
            stmt = select(Answer).where(Answer.id == answer_id)
            result = self.db.execute(stmt).scalar_one_or_none()

            if result is None:
                raise NotFoundError(f"Answer not found: {answer_id}")

            return result

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get answer {answer_id}: {e}")
            raise DatabaseError(f"Answer fetch failed: {e}")

    def get_answer_by_query(self, query_id: UUID) -> AnswerORM | None:
        """
        Get answer for a query.

        Args:
            query_id: Query UUID

        Returns:
            Answer instance or None if not found

        Raises:
            DatabaseError: If query fails
        """
        try:
            stmt = select(Answer).where(Answer.query_id == query_id)
            result = self.db.execute(stmt).scalar_one_or_none()

            return result

        except Exception as e:
            logger.error(f"Failed to get answer for query {query_id}: {e}")
            raise DatabaseError(f"Answer fetch failed: {e}")

    # Query result operations

    def create_query_result(self, query_result: QueryResultORM) -> QueryResultORM:
        """
        Create a query result (retrieved chunk).

        Args:
            query_result: Query result instance

        Returns:
            Created query result

        Raises:
            DatabaseError: If creation fails
        """
        try:
            self.db.add(query_result)
            self.db.commit()
            self.db.refresh(query_result)

            return query_result

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create query result: {e}")
            raise DatabaseError(f"Query result creation failed: {e}")

    def create_query_results_bulk(
        self, query_results: list[QueryResultORM]
    ) -> list[QueryResultORM]:
        """
        Create multiple query results in bulk.

        Args:
            query_results: List of query result instances

        Returns:
            List of created query results

        Raises:
            DatabaseError: If creation fails
        """
        try:
            self.db.bulk_save_objects(query_results, return_defaults=True)
            self.db.commit()

            logger.info(f"Created {len(query_results)} query results in bulk")
            return query_results

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create query results in bulk: {e}")
            raise DatabaseError(f"Bulk query result creation failed: {e}")

    def get_query_results(
        self,
        query_id: UUID,
        limit: int = 50,
    ) -> list[QueryResultORM]:
        """
        Get all query results for a query.

        Args:
            query_id: Query UUID
            limit: Maximum results

        Returns:
            List of query results ordered by rank

        Raises:
            DatabaseError: If query fails
        """
        try:
            stmt = (
                select(QueryResultORM)
                .where(QueryResultORM.query_id == query_id)
                .order_by(QueryResultORM.rank)
                .limit(limit)
            )

            results = self.db.execute(stmt).scalars().all()
            return list(results)

        except Exception as e:
            logger.error(f"Failed to get query results for {query_id}: {e}")
            raise DatabaseError(f"Query results fetch failed: {e}")

    # Combined operations

    def get_query_with_answer(self, query_id: UUID) -> tuple[QueryORM, AnswerORM | None]:
        """
        Get query and its answer (if exists).

        Args:
            query_id: Query UUID

        Returns:
            Tuple of (Query, Answer or None)

        Raises:
            NotFoundError: If query not found
            DatabaseError: If query fails
        """
        try:
            query = self.get_query(query_id)
            answer = self.get_answer_by_query(query_id)

            return query, answer

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get query with answer {query_id}: {e}")
            raise DatabaseError(f"Query fetch failed: {e}")

    # Statistics

    def count_queries(
        self,
        user_id: str | None = None,
        status: ProcessingStatus | None = None,
        collection_name: str | None = None,
    ) -> int:
        """
        Count queries with optional filters.

        Args:
            user_id: Filter by user
            status: Filter by status
            collection_name: Filter by collection

        Returns:
            Query count

        Raises:
            DatabaseError: If query fails
        """
        try:
            stmt = select(func.count(Query.id))

            conditions = []
            if user_id:
                conditions.append(Query.user_id == user_id)
            if status:
                conditions.append(Query.status == status)
            if collection_name:
                conditions.append(Query.collection_name == collection_name)

            if conditions:
                stmt = stmt.where(and_(*conditions))

            count = self.db.execute(stmt).scalar()
            return count or 0

        except Exception as e:
            logger.error(f"Failed to count queries: {e}")
            raise DatabaseError(f"Query count failed: {e}")

    def get_average_confidence_score(
        self,
        collection_name: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> float:
        """
        Get average confidence score for answers.

        Args:
            collection_name: Filter by collection
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            Average confidence score

        Raises:
            DatabaseError: If query fails
        """
        try:
            stmt = select(func.avg(Answer.confidence_score))

            # Join with queries if filtering by collection or date
            if collection_name or start_date or end_date:
                stmt = stmt.join(Query, Answer.query_id == Query.id)

                conditions = []
                if collection_name:
                    conditions.append(Query.collection_name == collection_name)
                if start_date:
                    conditions.append(Query.submitted_at >= start_date)
                if end_date:
                    conditions.append(Query.submitted_at <= end_date)

                if conditions:
                    stmt = stmt.where(and_(*conditions))

            avg_score = self.db.execute(stmt).scalar()
            return float(avg_score) if avg_score else 0.0

        except Exception as e:
            logger.error(f"Failed to get average confidence score: {e}")
            raise DatabaseError(f"Confidence score query failed: {e}")

    # Helper methods for API layer
    def create(
        self,
        query_id: str,
        question: str,
        collection: str,
        max_chunks: int,
    ) -> QueryORM:
        """
        Simplified create method for API layer.

        Note: collection parameter name kept for API compatibility,
        but internally uses collection_name.
        """
        from uuid import UUID
        from datetime import datetime

        try:
            query_obj = QueryORM(
                id=UUID(query_id),
                query_text=question,
                collection_name=collection,
                language_code='pt-BR',
                status=ProcessingStatus.PENDING,
                submitted_at=datetime.utcnow(),
            )

            self.db.add(query_obj)
            self.db.commit()
            self.db.refresh(query_obj)

            logger.info(f"Created query: {query_obj.id}")
            return query_obj

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create query: {e}")
            raise DatabaseError(f"Query creation failed: {e}")

    def get_by_id(self, query_id: str) -> Any:
        """Get query by ID string (wrapper for get_query)."""
        from uuid import UUID
        return self.get_query(UUID(query_id))

    def update_status(self, query_id: str, status: Any) -> None:
        """Update query status by ID string."""
        from uuid import UUID
        return self.update_query_status(UUID(query_id), status)
