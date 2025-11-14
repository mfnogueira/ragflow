"""Process and clean Olist reviews CSV for RAG system."""

import csv
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    if not text or text.strip() == "":
        return ""

    # Remove extra whitespace
    text = " ".join(text.split())

    # Remove common noise
    text = text.strip()

    return text


def process_review(row: Dict[str, str]) -> Dict[str, Any] | None:
    """
    Process a single review row.

    Returns formatted review or None if invalid.
    """
    # Extract and clean fields
    review_id = row.get("review_id", "").strip()
    order_id = row.get("order_id", "").strip()
    score = row.get("review_score", "").strip()
    title = clean_text(row.get("review_comment_title", ""))
    message = clean_text(row.get("review_comment_message", ""))
    category = clean_text(row.get("product_category", ""))
    creation_date = row.get("review_creation_date", "").strip()

    # Validation: skip if no meaningful content
    if not message and not title:
        return None

    # Validate score
    try:
        score_int = int(score)
        if score_int < 1 or score_int > 5:
            return None
    except (ValueError, TypeError):
        return None

    # Combine title and message into full review text
    review_parts = []
    if title:
        review_parts.append(f"Título: {title}")
    if message:
        review_parts.append(f"Comentário: {message}")

    full_text = "\n".join(review_parts)

    # Determine sentiment label
    sentiment_map = {
        1: "muito_negativo",
        2: "negativo",
        3: "neutro",
        4: "positivo",
        5: "muito_positivo",
    }
    sentiment = sentiment_map.get(score_int, "desconhecido")

    # Create processed review
    processed = {
        "review_id": review_id,
        "order_id": order_id,
        "score": score_int,
        "sentiment": sentiment,
        "title": title,
        "message": message,
        "full_text": full_text,
        "category": category,
        "creation_date": creation_date,
        "text_length": len(full_text),
        "has_title": bool(title),
        "has_message": bool(message),
    }

    return processed


def process_reviews_csv(
    input_file: Path,
    output_file: Path,
    min_text_length: int = 10,
) -> List[Dict[str, Any]]:
    """
    Process reviews CSV and output cleaned JSON.

    Args:
        input_file: Path to input CSV
        output_file: Path to output JSON
        min_text_length: Minimum text length to keep review

    Returns:
        List of processed reviews
    """
    print(f"Processing reviews from: {input_file}")
    print()

    processed_reviews = []
    skipped_count = 0

    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for idx, row in enumerate(reader, 1):
            processed = process_review(row)

            if processed is None:
                skipped_count += 1
                continue

            # Filter by minimum length
            if processed["text_length"] < min_text_length:
                skipped_count += 1
                continue

            processed_reviews.append(processed)

    # Statistics
    print("Processing Statistics:")
    print(f"  Total rows read: {idx}")
    print(f"  Valid reviews: {len(processed_reviews)}")
    print(f"  Skipped reviews: {skipped_count}")
    print()

    # Sentiment distribution
    sentiment_counts = {}
    for review in processed_reviews:
        sentiment = review["sentiment"]
        sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1

    print("Sentiment Distribution:")
    for sentiment, count in sorted(sentiment_counts.items()):
        pct = (count / len(processed_reviews)) * 100
        print(f"  {sentiment}: {count} ({pct:.1f}%)")
    print()

    # Category distribution
    category_counts = {}
    for review in processed_reviews:
        cat = review["category"] or "sem_categoria"
        category_counts[cat] = category_counts.get(cat, 0) + 1

    print("Top 10 Categories:")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        pct = (count / len(processed_reviews)) * 100
        print(f"  {cat}: {count} ({pct:.1f}%)")
    print()

    # Save to JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(processed_reviews, f, ensure_ascii=False, indent=2)

    print(f"Saved processed reviews to: {output_file}")
    print()

    return processed_reviews


def create_documents_for_ingestion(
    processed_reviews: List[Dict[str, Any]],
    output_file: Path,
    collection: str = "olist_reviews",
) -> List[Dict[str, Any]]:
    """
    Create document format ready for API ingestion.

    Each review becomes a document with metadata.
    """
    print("Creating documents for ingestion...")

    documents = []

    for review in processed_reviews:
        # Create document content (what will be chunked and embedded)
        content = review["full_text"]

        # Add contextual information to help with retrieval
        enriched_content = f"""Review da categoria: {review['category']}
Avaliação: {review['score']} estrelas ({review['sentiment']})
Data: {review['creation_date']}

{content}
"""

        # Create document metadata
        doc = {
            "content": enriched_content,
            "source": f"olist_review_{review['review_id']}",
            "collection": collection,
            "metadata": {
                "review_id": review["review_id"],
                "order_id": review["order_id"],
                "score": review["score"],
                "sentiment": review["sentiment"],
                "category": review["category"],
                "creation_date": review["creation_date"],
                "text_length": review["text_length"],
                "has_title": review["has_title"],
                "has_message": review["has_message"],
                "title": review["title"],
            }
        }

        documents.append(doc)

    # Save documents
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)

    print(f"Created {len(documents)} documents")
    print(f"Saved to: {output_file}")
    print()

    # Show sample
    print("Sample document:")
    print(json.dumps(documents[0], ensure_ascii=False, indent=2))
    print()

    return documents


if __name__ == "__main__":
    # Paths
    project_root = Path(__file__).parent.parent
    input_csv = project_root / "sample_data" / "olist_reviews_sample.csv"
    output_json = project_root / "sample_data" / "processed_reviews.json"
    output_docs = project_root / "sample_data" / "documents_for_ingestion.json"

    print("="*60)
    print("OLIST REVIEWS PROCESSING PIPELINE")
    print("="*60)
    print()

    # Step 1: Process and clean reviews
    processed = process_reviews_csv(input_csv, output_json)

    # Step 2: Create documents for ingestion
    documents = create_documents_for_ingestion(processed, output_docs)

    print("="*60)
    print("PROCESSING COMPLETE!")
    print("="*60)
    print()
    print("Next steps:")
    print("  1. Review processed data in:", output_json)
    print("  2. Review documents in:", output_docs)
    print("  3. Run ingest script to load into database")
    print()
