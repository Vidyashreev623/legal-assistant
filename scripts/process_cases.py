import os
import re
import json
import hashlib
from pathlib import Path

try:
    import pymupdf
except ImportError:
    print("ERROR: pymupdf is not installed.")
    print("Install it using:")
    print("    pip install pymupdf")
    raise


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATASET_DIR = BASE_DIR / "dataset"
OUTPUT_DIR = BASE_DIR / "processed" / "cases"

DOMAINS = [
    "consumer",
    "contract",
    "cyber",
    "family",
    "property",
    "employment",
]


# ============================================================
# BASIC UTILITIES
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


def clean_text(text):
    """Clean extracted PDF text."""

    if not text:
        return ""

    # Normalize line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove excessive spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_pdf_text(pdf_path):
    """Extract all text from a PDF."""

    try:
        document = pymupdf.open(pdf_path)

        pages = []

        for page in document:
            page_text = page.get_text()

            if page_text:
                pages.append(page_text)

        document.close()

        return clean_text("\n".join(pages))

    except Exception as e:
        print(f"    ERROR extracting PDF: {e}")
        return ""


# ============================================================
# FILENAME PROCESSING
# ============================================================

def remove_duplicate_suffix(filename):
    """
    Convert:
        Case_Name (1).PDF
        Case_Name (2).PDF
        Case_Name (3).PDF

    into:
        Case_Name.PDF

    Used only for detecting duplicate filename variants.
    """

    name = Path(filename).stem

    name = re.sub(r"\s*\(\d+\)$", "", name)

    return name.lower().strip()


def filename_to_case_name(filename):
    """Convert filename into readable case name."""

    name = Path(filename).stem

    # Remove duplicate suffix
    name = re.sub(r"\s*\(\d+\)$", "", name)

    # Remove date
    name = re.sub(
        r"_on_\d{1,2}_\w+_\d{4}$",
        "",
        name,
        flags=re.IGNORECASE
    )

    # Special case
    name = re.sub(
        r"_on_\d{1,2}_\w+_\d{4}_\d*$",
        "",
        name,
        flags=re.IGNORECASE
    )

    # Replace underscores
    name = name.replace("_", " ")

    # Clean multiple spaces
    name = re.sub(r"\s+", " ", name)

    return name.strip()


def extract_date_from_filename(filename):
    """
    Extract date from filenames such as:

    A_Ramkumar_vs_The_Chairman_on_29_October_2025.PDF
    """

    name = Path(filename).stem

    match = re.search(
        r"_on_(\d{1,2})_([A-Za-z]+)_(\d{4})",
        name,
        flags=re.IGNORECASE
    )

    if match:
        day = match.group(1)
        month = match.group(2)
        year = match.group(3)

        return f"{day} {month} {year}"

    return ""


# ============================================================
# CASE NAME FROM DOCUMENT
# ============================================================

def extract_case_name_from_text(text):
    """
    Try to extract the case name from the judgment itself.

    Example:

    A.Ramkumar vs The Chairman on 29 October, 2025
    """

    if not text:
        return None

    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # Look at the first 30 lines
    for line in lines[:30]:

        # Common Indian judgment pattern
        if re.search(r"\bvs\.?\b", line, re.IGNORECASE):
            line = re.sub(
                r"\s+on\s+\d{1,2}\s+\w+,?\s+\d{4}.*$",
                "",
                line,
                flags=re.IGNORECASE
            )

            if 5 < len(line) < 300:
                return line.strip()

    return None


# ============================================================
# COURT DETECTION
# ============================================================

def detect_court(text, source_path):
    """
    Detect court/forum from the actual judgment text.

    Priority is important:
        Supreme Court
        High Court
        NCDRC
        State Consumer Commission
        District Consumer Commission
        Tribunal
        Other
    """

    text_upper = text.upper()

    # --------------------------------------------------------
    # SUPREME COURT
    # --------------------------------------------------------

    supreme_patterns = [
        "SUPREME COURT OF INDIA",
        "IN THE SUPREME COURT OF INDIA",
        "BEFORE THE SUPREME COURT",
    ]

    if any(pattern in text_upper for pattern in supreme_patterns):
        return "supreme_court"

    # --------------------------------------------------------
    # HIGH COURT
    # --------------------------------------------------------

    high_court_patterns = [
        "HIGH COURT OF JUDICATURE",
        "HIGH COURT OF",
        "IN THE HIGH COURT",
        "BEFORE THE HIGH COURT",
    ]

    if any(pattern in text_upper for pattern in high_court_patterns):
        return "high_court"

    # --------------------------------------------------------
    # NCDRC
    # --------------------------------------------------------

    ncdrc_patterns = [
        "NATIONAL CONSUMER DISPUTES REDRESSAL COMMISSION",
        "NATIONAL CONSUMER DISPUTES REDRESSAL",
        "NCDRC",
    ]

    if any(pattern in text_upper for pattern in ncdrc_patterns):
        return "ncdrc"

    # --------------------------------------------------------
    # STATE CONSUMER COMMISSION
    # --------------------------------------------------------

    state_patterns = [
        "STATE CONSUMER DISPUTES REDRESSAL COMMISSION",
        "STATE CONSUMER DISPUTES REDRESSAL",
        "STATE CONSUMER COMMISSION",
    ]

    if any(pattern in text_upper for pattern in state_patterns):
        return "state_consumer_commission"

    # --------------------------------------------------------
    # DISTRICT CONSUMER COMMISSION
    # --------------------------------------------------------

    district_patterns = [
        "DISTRICT CONSUMER DISPUTES REDRESSAL COMMISSION",
        "DISTRICT CONSUMER DISPUTES REDRESSAL",
        "DISTRICT CONSUMER COMMISSION",
        "DISTRICT CONSUMER FORUM",
        "DISTRICT FORUM",
    ]

    if any(pattern in text_upper for pattern in district_patterns):
        return "district_consumer_commission"

    # --------------------------------------------------------
    # TRIBUNALS
    # --------------------------------------------------------

    tribunal_patterns = [
        "CENTRAL ADMINISTRATIVE TRIBUNAL",
        "ARMED FORCES TRIBUNAL",
        "NATIONAL GREEN TRIBUNAL",
        "APPELLATE TRIBUNAL",
        "INCOME TAX APPELLATE TRIBUNAL",
        "TRIBUNAL",
    ]

    if any(pattern in text_upper for pattern in tribunal_patterns):
        return "tribunal"

    # --------------------------------------------------------
    # OTHER COMMISSIONS / FORUMS
    # --------------------------------------------------------

    commission_patterns = [
        "CONSUMER DISPUTES REDRESSAL COMMISSION",
        "CONSUMER DISPUTES REDRESSAL FORUM",
    ]

    if any(pattern in text_upper for pattern in commission_patterns):
        return "consumer_commission"

    # --------------------------------------------------------
    # FALLBACK BASED ON DIRECTORY
    # --------------------------------------------------------

    source_lower = str(source_path).lower()

    if "district_commissions" in source_lower:
        return "district_consumer_commission"

    if "state_commission" in source_lower:
        return "state_consumer_commission"

    if "ncdrc" in source_lower:
        return "ncdrc"

    if "supreme_court" in source_lower:
        return "supreme_court"

    if "high_court" in source_lower:
        return "high_court"

    # --------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------

    return "other"


# ============================================================
# DOCUMENT TYPE
# ============================================================

def detect_document_type(text, filename):
    """Detect whether document appears to be a judgment/order/etc."""

    text_upper = text.upper()
    filename_upper = filename.upper()

    if "JUDGMENT" in text_upper:
        return "judgment"

    if "ORDER" in text_upper:
        return "order"

    if "JUDGMENT" in filename_upper:
        return "judgment"

    if "ORDER" in filename_upper:
        return "order"

    return "case_document"


# ============================================================
# CASE RECORD
# ============================================================

def create_case_record(
    domain,
    pdf_path,
    text,
    file_hash,
    case_number
):
    """Create structured JSON record."""

    filename = pdf_path.name

    case_name = extract_case_name_from_text(text)

    if not case_name:
        case_name = filename_to_case_name(filename)

    date = extract_date_from_filename(filename)

    court = detect_court(text, pdf_path)

    document_type = detect_document_type(
        text,
        filename
    )

    record = {
        "id": f"{domain}_case_{case_number:05d}",
        "domain": domain,
        "case_name": case_name,
        "court": court,
        "date": date,
        "document_type": document_type,
        "source_file": filename,
        "source_path": str(
            pdf_path.relative_to(BASE_DIR)
        ).replace("\\", "/"),
        "file_hash": file_hash,
        "text": text,
    }

    return record


# ============================================================
# PROCESS ONE DOMAIN
# ============================================================

def process_domain(domain):

    print()
    print("=" * 70)
    print(f"PROCESSING: {domain.upper()}")
    print("=" * 70)

    domain_cases_dir = DATASET_DIR / domain / "cases"

    if not domain_cases_dir.exists():

        print(f"WARNING: Folder not found:")
        print(f"  {domain_cases_dir}")

        return []

    # Find PDFs recursively
    pdf_files = sorted(
        domain_cases_dir.rglob("*")
    )

    pdf_files = [
        p for p in pdf_files
        if p.is_file()
        and p.suffix.lower() == ".pdf"
    ]

    print(f"Found {len(pdf_files)} PDF files")

    records = []

    # Track duplicate filename variants
    processed_names = set()

    # Track exact file hashes
    processed_hashes = set()

    case_number = 1

    for pdf_path in pdf_files:

        filename = pdf_path.name

        # ----------------------------------------------------
        # DUPLICATE FILENAME VARIANT
        # ----------------------------------------------------

        normalized_name = remove_duplicate_suffix(
            filename
        )

        if normalized_name in processed_names:

            print(
                f"  SKIPPED: duplicate filename variant - "
                f"{filename}"
            )

            continue

        # ----------------------------------------------------
        # EXTRACT
        # ----------------------------------------------------

        print(f"  Extracting: {filename}")

        text = extract_pdf_text(pdf_path)

        if not text:

            print("    SKIPPED: no text extracted")

            continue

        # ----------------------------------------------------
        # HASH
        # ----------------------------------------------------

        file_hash = calculate_file_hash(
            pdf_path
        )

        # ----------------------------------------------------
        # EXACT DUPLICATE
        # ----------------------------------------------------

        if file_hash in processed_hashes:

            print("    SKIPPED: exact duplicate file")

            continue

        # ----------------------------------------------------
        # MARK AS PROCESSED
        # ----------------------------------------------------

        processed_names.add(
            normalized_name
        )

        processed_hashes.add(
            file_hash
        )

        # ----------------------------------------------------
        # CREATE RECORD
        # ----------------------------------------------------

        record = create_case_record(
            domain=domain,
            pdf_path=pdf_path,
            text=text,
            file_hash=file_hash,
            case_number=case_number
        )

        records.append(record)

        case_number += 1

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        OUTPUT_DIR /
        f"{domain}_cases.json"
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

    print()
    print(f"Cases processed: {len(records)}")
    print(f"Output: {output_file}")

    return records


# ============================================================
# VALIDATION
# ============================================================

def validate_record(record):

    required_fields = [
        "id",
        "domain",
        "case_name",
        "court",
        "date",
        "document_type",
        "source_file",
        "source_path",
        "file_hash",
        "text",
    ]

    missing = [
        field
        for field in required_fields
        if field not in record
    ]

    return missing


def validate_all_cases():

    print()
    print("=" * 70)
    print("VALIDATING PROCESSED CASE DATA")
    print("=" * 70)

    total = 0
    errors = 0

    json_files = sorted(
        OUTPUT_DIR.glob("*_cases.json")
    )

    for json_file in json_files:

        try:

            with open(
                json_file,
                "r",
                encoding="utf-8"
            ) as f:

                records = json.load(f)

            print(
                f"{json_file.name}: "
                f"{len(records)} records"
            )

            total += len(records)

            for record in records:

                missing = validate_record(
                    record
                )

                if missing:

                    errors += 1

                    print(
                        f"  ERROR: "
                        f"{record.get('id', 'UNKNOWN')} "
                        f"missing {missing}"
                    )

                if not record.get("text", "").strip():

                    errors += 1

                    print(
                        f"  ERROR: "
                        f"{record.get('id', 'UNKNOWN')} "
                        f"has empty text"
                    )

        except Exception as e:

            errors += 1

            print(
                f"  ERROR reading "
                f"{json_file.name}: {e}"
            )

    print()
    print("-" * 70)
    print(f"TOTAL CASES: {total}")
    print(f"VALIDATION ERRORS: {errors}")
    print("-" * 70)

    return total, errors


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("LEGAL ASSISTANT - CASE PROCESSING")
    print("=" * 70)

    total_cases = 0

    for domain in DOMAINS:

        records = process_domain(
            domain
        )

        total_cases += len(records)

    print()
    print("=" * 70)
    print("CASE PROCESSING COMPLETE")
    print("=" * 70)

    print(
        f"TOTAL CASES: {total_cases}"
    )

    # Validate everything after processing
    validate_all_cases()

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()