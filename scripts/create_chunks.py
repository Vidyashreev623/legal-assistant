import json
import re
from pathlib import Path

INPUT_FILE = Path("processed/master/legal_dataset.json")
OUTPUT_DIR = Path("processed/chunks")
OUTPUT_FILE = OUTPUT_DIR / "legal_chunks.json"

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


def clean_text(text):
    """Basic cleanup while preserving legal content."""
    if not text:
        return ""

    text = text.replace("\x00", " ")

    # Normalize excessive whitespace
    text = re.sub(r"[ \t]+", " ", text)

    # Normalize excessive blank lines
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    return text.strip()


def split_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end < len(text):
            # Prefer breaking at a paragraph or sentence
            candidates = [
                text.rfind("\n\n", start, end),
                text.rfind(". ", start, end),
                text.rfind("; ", start, end),
                text.rfind(" ", start, end),
            ]

            best_break = max(candidates)

            if best_break > start + chunk_size // 2:
                end = best_break + 1

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(end - overlap, start + 1)

    return chunks


def create_chunk(record, chunk_text, chunk_number, total_chunks):
    """Create a RAG-ready chunk while preserving source metadata."""

    chunk = {
        "chunk_id": f"{record['id']}_chunk_{chunk_number:04d}",
        "source_id": record["id"],
        "type": record["type"],
        "domain": record.get("domain"),
        "text": chunk_text,
        "chunk_number": chunk_number,
        "total_chunks": total_chunks,
    }

    # Preserve important legal metadata
    metadata_fields = [
        "act_name",
        "act",
        "section",
        "title",
        "case_name",
        "court",
        "date",
        "document_type",
        "year",
        "source_file",
        "source_path",
    ]

    for field in metadata_fields:
        if field in record:
            chunk[field] = record[field]

    return chunk


def main():
    print("=" * 70)
    print("LEGAL ASSISTANT - RAG CHUNK CREATION")
    print("=" * 70)

    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        return

    print(f"\nLoading: {INPUT_FILE}")

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"Source records: {len(records)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_chunks = []

    stats = {
        "acts": 0,
        "cases": 0,
        "rules": 0,
        "sections": 0,
    }

    for record in records:
        text = clean_text(record.get("text", ""))

        if not text:
            continue

        chunks = split_text(text)

        for i, chunk_text in enumerate(chunks, start=1):
            chunk = create_chunk(
                record,
                chunk_text,
                i,
                len(chunks),
            )

            all_chunks.append(chunk)

        record_type = record.get("type")

        if record_type in stats:
            stats[record_type] += len(chunks)

    print("\n" + "-" * 70)
    print("CHUNKING COMPLETE")
    print("-" * 70)

    print(f"Total chunks: {len(all_chunks)}")

    print("\nChunks by type:")

    for record_type, count in stats.items():
        print(f"  {record_type:<10}: {count}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            all_chunks,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("\nOutput:")
    print(OUTPUT_FILE.resolve())

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()