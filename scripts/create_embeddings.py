import json
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


# ============================================================
# LEGAL ASSISTANT - EMBEDDING CREATION
# ============================================================

INPUT_FILE = "processed/chunks/legal_chunks.json"
OUTPUT_DIR = "processed/embeddings"

INDEX_FILE = os.path.join(OUTPUT_DIR, "legal.index")
METADATA_FILE = os.path.join(OUTPUT_DIR, "chunk_metadata.json")

# Multilingual model suitable for English + Indian-language text
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

BATCH_SIZE = 32


def main():
    print("=" * 70)
    print("LEGAL ASSISTANT - EMBEDDING CREATION")
    print("=" * 70)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --------------------------------------------------------
    # Load chunks
    # --------------------------------------------------------
    print("\nLoading chunks...")

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"Total chunks: {len(chunks)}")

    if not chunks:
        raise ValueError("No chunks found.")

    # --------------------------------------------------------
    # Extract text
    # --------------------------------------------------------
    texts = [chunk["text"] for chunk in chunks]

    # --------------------------------------------------------
    # Load embedding model
    # --------------------------------------------------------
    print("\nLoading embedding model:")
    print(MODEL_NAME)

    model = SentenceTransformer(MODEL_NAME)

    print("Embedding dimension:", model.get_sentence_embedding_dimension())

    # --------------------------------------------------------
    # Generate embeddings
    # --------------------------------------------------------
    print("\nGenerating embeddings...")
    print(f"Batch size: {BATCH_SIZE}")

    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    embeddings = embeddings.astype("float32")

    print("\nEmbeddings generated.")
    print("Shape:", embeddings.shape)

    # --------------------------------------------------------
    # Create FAISS index
    # --------------------------------------------------------
    print("\nCreating FAISS index...")

    dimension = embeddings.shape[1]

    # Because embeddings are normalized,
    # inner product is equivalent to cosine similarity.
    index = faiss.IndexFlatIP(dimension)

    index.add(embeddings)

    print("FAISS vectors:", index.ntotal)

    # --------------------------------------------------------
    # Save FAISS index
    # --------------------------------------------------------
    faiss.write_index(index, INDEX_FILE)

    print(f"\nFAISS index saved:")
    print(INDEX_FILE)

    # --------------------------------------------------------
    # Save metadata
    # --------------------------------------------------------
    metadata = []

    for chunk in chunks:
        metadata.append({
            "chunk_id": chunk["chunk_id"],
            "source_id": chunk["source_id"],
            "type": chunk["type"],
            "domain": chunk["domain"],
            "chunk_number": chunk.get("chunk_number"),
            "total_chunks": chunk.get("total_chunks"),
            "act_name": chunk.get("act_name"),
            "year": chunk.get("year"),
            "source_file": chunk.get("source_file"),
            "source_path": chunk.get("source_path"),
            "text": chunk["text"]
        })

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            metadata,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"Metadata saved:")
    print(METADATA_FILE)

    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------
    print("\n" + "=" * 70)
    print("VALIDATING EMBEDDINGS")
    print("=" * 70)

    saved_index = faiss.read_index(INDEX_FILE)

    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        saved_metadata = json.load(f)

    print("FAISS vectors:", saved_index.ntotal)
    print("Metadata records:", len(saved_metadata))

    if saved_index.ntotal != len(chunks):
        raise ValueError("FAISS vector count does not match chunk count.")

    if len(saved_metadata) != len(chunks):
        raise ValueError("Metadata count does not match chunk count.")

    print("\nEmbedding validation PASSED")

    print("\n" + "=" * 70)
    print("EMBEDDING CREATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()