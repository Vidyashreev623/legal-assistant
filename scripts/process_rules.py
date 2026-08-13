import os
import json
import re
from pypdf import PdfReader


# ============================================================
# CONFIGURATION
# ============================================================

DATASET_DIR = "dataset"

DOMAINS = [
    "consumer",
    "contract",
    "cyber",
    "family",
    "property",
    "employment"
]

OUTPUT_DIR = os.path.join(
    "processed",
    "rules"
)


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = str(text)

    replacements = {
        "â€”": "—",
        "â€“": "–",
        "â€˜": "‘",
        "â€™": "’",
        "â€œ": "“",
        "â€\x9d": "”",
        "â€¦": "…",
        "Â ": " ",
        "\xa0": " "
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove excessive spaces
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Remove excessive blank lines
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# TITLE FROM FILENAME
# ============================================================

def title_from_filename(filename):

    title = os.path.splitext(
        filename
    )[0]

    # Replace underscores
    title = title.replace(
        "_",
        " "
    )

    # Replace repeated spaces
    title = re.sub(
        r"\s+",
        " ",
        title
    )

    return title.strip()


# ============================================================
# EXTRACT PDF
# ============================================================

def extract_pdf(path):

    try:

        reader = PdfReader(path)

    except Exception as e:

        print(
            f"ERROR opening PDF: {path}"
        )

        print(e)

        return ""

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1
    ):

        try:

            text = page.extract_text()

            if text:

                pages.append(text)

        except Exception as e:

            print(
                f"WARNING: Page {page_number} "
                f"failed in {os.path.basename(path)}"
            )

    return clean_text(
        "\n\n".join(pages)
    )


# ============================================================
# PROCESS DOMAIN
# ============================================================

def process_domain(domain):

    rules_dir = os.path.join(
        DATASET_DIR,
        domain,
        "rules"
    )

    if not os.path.exists(rules_dir):

        print(
            f"[SKIP] {domain}: rules folder not found"
        )

        return []

    results = []

    pdf_files = sorted(
        [
            f
            for f in os.listdir(rules_dir)
            if f.lower().endswith(".pdf")
        ]
    )

    if not pdf_files:

        print(
            f"[INFO] {domain}: no rule PDFs found"
        )

        return []

    for filename in pdf_files:

        path = os.path.join(
            rules_dir,
            filename
        )

        print(
            f"  Extracting: {filename}"
        )

        text = extract_pdf(
            path
        )

        if not text:

            print(
                "    WARNING: No text extracted"
            )

            continue

        results.append({

            "domain": domain,

            "document_type": "rule",

            "title": title_from_filename(
                filename
            ),

            "text": text,

            "source_file": filename

        })

    return results


# ============================================================
# MAIN
# ============================================================

def main():

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    total = 0

    print("=" * 70)
    print("LEGAL ASSISTANT - RULE PROCESSING")
    print("=" * 70)

    for domain in DOMAINS:

        print("\n")
        print("=" * 70)
        print(
            f"PROCESSING: {domain.upper()}"
        )
        print("=" * 70)

        records = process_domain(
            domain
        )

        output_file = os.path.join(
            OUTPUT_DIR,
            f"{domain}_rules.json"
        )

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                records,
                f,
                ensure_ascii=False,
                indent=2
            )

        print(
            f"Rules processed: {len(records)}"
        )

        print(
            f"Output: {output_file}"
        )

        total += len(records)

    print("\n")
    print("=" * 70)
    print("RULE PROCESSING COMPLETE")
    print("=" * 70)

    print(
        f"TOTAL RULE DOCUMENTS: {total}"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()