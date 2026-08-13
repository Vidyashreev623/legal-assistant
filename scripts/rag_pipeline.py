import os
from google import genai

from retriever import retrieve


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY environment variable not found."
    )

client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-2.5-flash"


# ============================================================
# BUILD LEGAL CONTEXT
# ============================================================

def build_context(results):
    context_parts = []

    for i, result in enumerate(results, start=1):

        source = result.get("source_file", "Unknown source")
        domain = result.get("domain", "Unknown domain")
        record_type = result.get("type", "Unknown type")
        score = result.get("similarity_score", 0)

        context_parts.append(
            f"""
SOURCE {i}
Domain: {domain}
Type: {record_type}
Source: {source}
Similarity: {score:.4f}

TEXT:
{result.get("text", "")}
"""
        )

    return "\n".join(context_parts)


# ============================================================
# GENERATE LEGAL ANSWER
# ============================================================

def generate_answer(question, top_k=5):

    results = retrieve(question, top_k=top_k)

    if not results:
        return {
            "answer": "I could not find relevant legal information in the dataset.",
            "sources": []
        }

    context = build_context(results)

    prompt = f"""
You are a legal information assistant for an Indian law RAG system.

Answer the user's question ONLY using the legal information
provided in the CONTEXT below.

Important rules:

1. Do not invent legal provisions, sections, cases, penalties,
   procedures, or facts.
2. If the context does not contain enough information to answer
   the question, clearly say that the available dataset does not
   contain enough information.
3. Prefer the most relevant legal section or provision when available.
4. Explain the answer clearly and concisely.
5. Mention the relevant Act and section when that information is
   available in the context.
6. Do not treat similarity scores as legal authority.
7. This is a legal information system, not a substitute for
   professional legal advice.

USER QUESTION:
{question}

CONTEXT:
{context}

Now provide a grounded answer based only on the context.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    sources = []

    for result in results:
        sources.append({
            "chunk_id": result.get("chunk_id"),
            "type": result.get("type"),
            "domain": result.get("domain"),
            "source_file": result.get("source_file"),
            "similarity_score": result.get("similarity_score")
        })

    return {
        "answer": response.text,
        "sources": sources
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("\n" + "=" * 70)
    print("LEGAL RAG PIPELINE TEST")
    print("=" * 70)

    question = "What are the essentials of a valid contract?"

    print("\nQUESTION:")
    print(question)

    result = generate_answer(question, top_k=5)

    print("\n" + "-" * 70)
    print("GENERATED ANSWER")
    print("-" * 70)

    print(result["answer"])

    print("\n" + "-" * 70)
    print("SOURCES")
    print("-" * 70)

    for source in result["sources"]:
        print(
            f"{source['type']} | "
            f"{source['domain']} | "
            f"{source['source_file']} | "
            f"score={source['similarity_score']:.4f}"
        )

    print("\n" + "=" * 70)
    print("RAG PIPELINE TEST COMPLETE")
    print("=" * 70)