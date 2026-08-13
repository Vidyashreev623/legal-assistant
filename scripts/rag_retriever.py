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


def retrieve_candidates(query, top_k=15):
    """
    Retrieve a larger candidate set from FAISS.
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


def rerank_results(query, candidates, top_k=5):
    """
    Lightweight legal-source reranking.

    Primary legal sources are preferred for questions
    asking about laws, sections, rights, duties, offences,
    punishments, procedures, etc.
    """

    query_lower = query.lower()

    legal_keywords = [
        "act",
        "section",
        "law",
        "legal",
        "rights",
        "right",
        "duty",
        "duties",
        "punishment",
        "offence",
        "offense",
        "procedure",
        "provision",
        "provisions",
        "penalty",
        "liable",
        "under"
    ]

    prefers_primary_law = any(
        keyword in query_lower
        for keyword in legal_keywords
    )

    reranked = []

    for chunk in candidates:

        score = chunk["similarity_score"]

        if prefers_primary_law:

            if chunk["type"] == "sections":
                score += 0.08

            elif chunk["type"] == "acts":
                score += 0.05

            elif chunk["type"] == "rules":
                score += 0.03

            elif chunk["type"] == "cases":
                score -= 0.03

        chunk["rerank_score"] = score

        reranked.append(chunk)

    reranked.sort(
        key=lambda x: x["rerank_score"],
        reverse=True
    )

    return reranked[:top_k]


def retrieve(query, top_k=5):
    """
    Complete retrieval pipeline:
    FAISS candidate retrieval + lightweight reranking.
    """

    candidates = retrieve_candidates(
        query,
        top_k=15
    )

    results = rerank_results(
        query,
        candidates,
        top_k=top_k
    )

    return results


if __name__ == "__main__":

    queries = [
        "What is the punishment for identity theft?",
        "What are the rights of a consumer under the Consumer Protection Act?",
        "What is the procedure for divorce under Hindu law?"
    ]

    print("\n" + "=" * 70)
    print("IMPROVED LEGAL RETRIEVER TEST")
    print("=" * 70)

    for query in queries:

        print("\n" + "=" * 70)
        print("QUERY:", query)
        print("=" * 70)

        results = retrieve(query, top_k=5)

        for i, result in enumerate(results, start=1):

            print("\n" + "-" * 70)
            print(f"RESULT {i}")
            print("-" * 70)

            print(
                "Similarity:",
                round(result["similarity_score"], 4)
            )

            print(
                "Rerank score:",
                round(result["rerank_score"], 4)
            )

            print("Type:", result["type"])
            print("Domain:", result["domain"])
            print("Source:", result["source_file"])
            print("Chunk ID:", result["chunk_id"])

            if result.get("act_name"):
                print("Act:", result["act_name"])

            print("\nText:")
            print(result["text"][:1000])

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)