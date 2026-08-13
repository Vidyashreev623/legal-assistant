import json
import faiss
from sentence_transformers import SentenceTransformer


INDEX_FILE = "processed/embeddings/legal.index"
METADATA_FILE = "processed/embeddings/chunk_metadata.json"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


print("Loading FAISS index...")
index = faiss.read_index(INDEX_FILE)

print("Loading metadata...")
with open(METADATA_FILE, "r", encoding="utf-8") as f:
    metadata = json.load(f)

print("Loading embedding model...")
model = SentenceTransformer(MODEL_NAME)


def retrieve(query, top_k=5):
    """
    Retrieve the most relevant legal chunks for a query.
    """

    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype("float32")

    scores, indices = index.search(query_embedding, top_k)

    results = []

    for score, idx in zip(scores[0], indices[0]):

        if idx < 0:
            continue

        chunk = metadata[idx].copy()
        chunk["similarity_score"] = float(score)

        results.append(chunk)

    return results


if __name__ == "__main__":

    query = "What is identity theft?"

    print("\n" + "=" * 70)
    print("LEGAL RETRIEVER TEST")
    print("=" * 70)

    print(f"\nQuery: {query}")

    results = retrieve(query, top_k=5)

    for i, result in enumerate(results, start=1):

        print("\n" + "-" * 70)
        print(f"RESULT {i}")
        print("-" * 70)

        print("Similarity:", round(result["similarity_score"], 4))
        print("Type:", result["type"])
        print("Domain:", result["domain"])
        print("Source:", result["source_file"])
        print("Chunk ID:", result["chunk_id"])

        if result.get("act_name"):
            print("Act:", result["act_name"])

        print("\nText:")
        print(result["text"][:1500])

    print("\n" + "=" * 70)
    print("RETRIEVER TEST COMPLETE")
    print("=" * 70)