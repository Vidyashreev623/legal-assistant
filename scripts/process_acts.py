import os
import re
import json
import hashlib
from pathlib import Path

from pypdf import PdfReader


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATASET_DIR = BASE_DIR / "dataset"
OUTPUT_DIR = BASE_DIR / "processed" / "acts"

DOMAINS = [
    "consumer",
    "contract",
    "cyber",
    "family",
    "property",
    "employment",
]


# ============================================================
# HELPERS
# ============================================================

def calculate_file_hash(file_path):
    """Calculate SHA-256 hash of a file."""

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF."""

    try:
        reader = PdfReader(str(pdf_path))

        pages = []

        for page in reader.pages:
            try:
                text = page.extract_text()

                if text:
                    pages.append(text)

            except Exception as e:
                print(f"    WARNING: Could not extract a page: {e}")

        return "\n".join(pages).strip()

    except Exception as e:
        print(f"    ERROR extracting PDF: {e}")
        return ""


def clean_text(text):
    """Clean extracted PDF text while preserving useful content."""

    if not text:
        return ""

    # Normalize line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove excessive spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

    return text.strip()


def detect_year(filename, text):
    """
    Try to detect the Act year from filename first,
    then from the extracted text.
    """

    # Common year pattern
    years = re.findall(r"\b(18\d{2}|19\d{2}|20\d{2})\b", filename)

    if years:
        return int(years[-1])

    # Try the first part of the document
    first_part = text[:5000]

    years = re.findall(r"\b(18\d{2}|19\d{2}|20\d{2})\b", first_part)

    if years:
        return int(years[0])

    return None


def clean_act_name(filename):
    """
    Convert filename into a readable Act name.
    """

    name = Path(filename).stem

    # Replace underscores and hyphens
    name = name.replace("_", " ")
    name = name.replace("-", " ")

    # Remove duplicate spaces
    name = re.sub(r"\s+", " ", name)

    # Normalize common naming
    name = name.strip()

    return name


def get_pdf_files(domain):
    """Return PDF files for a domain."""

    acts_dir = DATASET_DIR / domain / "acts"

    if not acts_dir.exists():
        return []

    files = []

    for file_path in acts_dir.iterdir():

        if not file_path.is_file():
            continue

        if file_path.name.lower() == ".gitkeep":
            continue

        if file_path.suffix.lower() != ".pdf":
            continue

        files.append(file_path)

    return sorted(files, key=lambda x: x.name.lower())


# ============================================================
# PROCESS ONE DOMAIN
# ============================================================

def process_domain(domain, global_hashes):

    print("=" * 70)
    print(f"PROCESSING: {domain.upper()}")
    print("=" * 70)

    pdf_files = get_pdf_files(domain)

    print(f"Found {len(pdf_files)} PDF files")

    records = []

    seen_hashes = set()

    skipped = 0
    errors = 0

    for pdf_path in pdf_files:

        print(f"  Extracting: {pdf_path.name}")

        # ----------------------------------------------------
        # Calculate hash
        # ----------------------------------------------------

        try:
            file_hash = calculate_file_hash(pdf_path)

        except Exception as e:
            print(f"  ERROR: Could not hash file: {e}")
            errors += 1
            continue

        # ----------------------------------------------------
        # Duplicate detection
        # ----------------------------------------------------

        if file_hash in seen_hashes:

            print(f"  SKIPPED: duplicate file content - {pdf_path.name}")

            skipped += 1
            continue

        if file_hash in global_hashes:

            print(f"  SKIPPED: duplicate file across domains - {pdf_path.name}")

            skipped += 1
            continue

        seen_hashes.add(file_hash)
        global_hashes.add(file_hash)

        # ----------------------------------------------------
        # Extract text
        # ----------------------------------------------------

        text = extract_text_from_pdf(pdf_path)

        if not text:

            print(f"  WARNING: No text extracted - {pdf_path.name}")

            errors += 1
            continue

        text = clean_text(text)

        # ----------------------------------------------------
        # Detect metadata
        # ----------------------------------------------------

        year = detect_year(pdf_path.name, text)

        act_name = clean_act_name(pdf_path.name)

        relative_path = pdf_path.relative_to(BASE_DIR)

        # ----------------------------------------------------
        # Create record
        # ----------------------------------------------------

        record = {
            "id": f"{domain}_act_{len(records) + 1:05d}",
            "domain": domain,
            "act_name": act_name,
            "year": year,
            "source_file": pdf_path.name,
            "source_path": str(relative_path).replace("\\", "/"),
            "file_hash": file_hash,
            "text": text
        }

        records.append(record)

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / f"{domain}_acts.json"

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

    print()
    print(f"Acts processed: {len(records)}")
    print(f"Duplicates skipped: {skipped}")
    print(f"Errors/warnings: {errors}")
    print(f"Output: {output_file}")
    print()

    return len(records), errors


# ============================================================
# VALIDATE OUTPUT
# ============================================================

def validate_json_file(json_file):

    try:

        with open(
            json_file,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if not isinstance(data, list):
            return 1, "JSON root is not a list"

        required_fields = [
            "id",
            "domain",
            "act_name",
            "source_file",
            "source_path",
            "file_hash",
            "text"
        ]

        errors = 0

        for index, record in enumerate(data):

            for field in required_fields:

                if field not in record:
                    print(
                        f"  ERROR: {json_file.name} "
                        f"record {index} missing '{field}'"
                    )

                    errors += 1

            if not record.get("text"):
                print(
                    f"  ERROR: {json_file.name} "
                    f"record {index} has empty text"
                )

                errors += 1

        return errors, None

    except Exception as e:

        return 1, str(e)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("LEGAL ASSISTANT - ACT PROCESSING")
    print("=" * 70)
    print()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    global_hashes = set()

    total_records = 0
    total_errors = 0

    # --------------------------------------------------------
    # Process all domains
    # --------------------------------------------------------

    for domain in DOMAINS:

        count, errors = process_domain(
            domain,
            global_hashes
        )

        total_records += count
        total_errors += errors

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    print("=" * 70)
    print("ACT PROCESSING COMPLETE")
    print("=" * 70)

    print(f"TOTAL ACTS: {total_records}")

    print()
    print("=" * 70)
    print("VALIDATING PROCESSED ACT DATA")
    print("=" * 70)

    validation_errors = 0

    json_files = sorted(
        OUTPUT_DIR.glob("*_acts.json")
    )

    for json_file in json_files:

        try:

            with open(
                json_file,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            print(
                f"{json_file.name}: "
                f"{len(data)} records"
            )

            errors, message = validate_json_file(
                json_file
            )

            validation_errors += errors

            if message:
                print(
                    f"  ERROR: {message}"
                )

        except Exception as e:

            print(
                f"{json_file.name}: ERROR - {e}"
            )

            validation_errors += 1

    print()
    print("-" * 70)

    print(
        f"TOTAL ACTS: {total_records}"
    )

    print(
        f"PROCESSING ERRORS/WARNINGS: {total_errors}"
    )

    print(
        f"VALIDATION ERRORS: {validation_errors}"
    )

    print("-" * 70)

    if validation_errors == 0:

        print("ACT DATA VALIDATION PASSED")

    else:

        print("ACT DATA VALIDATION FAILED")

    print("=" * 70)


if __name__ == "__main__":
    main()