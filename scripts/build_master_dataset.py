import json
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "processed"
OUTPUT_DIR = PROCESSED_DIR / "master"

OUTPUT_FILE = OUTPUT_DIR / "legal_dataset.json"
STATS_FILE = OUTPUT_DIR / "dataset_statistics.json"


def load_json(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            print(f"WARNING: {file_path.name} is not a list")
            return []

        return data

    except Exception as e:
        print(f"ERROR reading {file_path}: {e}")
        return []


def get_domain(file_path, data_type):
    """
    Example:
        consumer_acts.json -> consumer
        contract_cases.json -> contract
    """

    stem = file_path.stem
    suffix = "_" + data_type

    if stem.endswith(suffix):
        return stem[:-len(suffix)]

    return stem


def process_category(data_type):

    directory = PROCESSED_DIR / data_type

    if not directory.exists():
        print(f"WARNING: {directory} does not exist")
        return []

    records = []

    files = sorted(directory.glob("*.json"))

    print()
    print("=" * 70)
    print(f"PROCESSING {data_type.upper()}")
    print("=" * 70)

    for file_path in files:

        # Never process master files
        if file_path.parent == OUTPUT_DIR:
            continue

        domain = get_domain(file_path, data_type)

        data = load_json(file_path)

        print(
            f"{file_path.name}: "
            f"{len(data)} records"
        )

        for index, record in enumerate(data, start=1):

            record = dict(record)

            # ------------------------------------------------
            # IMPORTANT:
            # Create a globally unique ID.
            # ------------------------------------------------

            old_id = record.get("id", "")

            new_id = f"{data_type}_{domain}_{index:06d}"

            record["id"] = new_id

            # ------------------------------------------------
            # Common metadata
            # ------------------------------------------------

            record["domain"] = record.get(
                "domain",
                domain
            )

            record["type"] = data_type

            record["source_file"] = record.get(
                "source_file"
            )

            record["source_path"] = record.get(
                "source_path"
            )

            record["text"] = record.get(
                "text",
                ""
            )

            if record["text"] is None:
                record["text"] = ""

            record["text"] = str(record["text"])

            # Keep original ID for traceability
            if old_id:
                record["original_id"] = old_id

            records.append(record)

    print(
        f"Total {data_type}: {len(records)}"
    )

    return records


def validate(records):

    errors = []

    required_fields = [
        "id",
        "domain",
        "type",
        "text"
    ]

    ids = set()

    for i, record in enumerate(records):

        for field in required_fields:

            if field not in record:
                errors.append(
                    f"Record {i}: missing {field}"
                )

        record_id = record.get("id")

        if not record_id:
            errors.append(
                f"Record {i}: empty ID"
            )

        if record_id in ids:
            errors.append(
                f"Record {i}: duplicate ID {record_id}"
            )

        ids.add(record_id)

        if not isinstance(
            record.get("text"),
            str
        ):
            errors.append(
                f"Record {i}: text is not string"
            )

    return errors


def main():

    print("=" * 70)
    print("LEGAL ASSISTANT - MASTER DATASET BUILDER")
    print("=" * 70)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    all_records = []

    # --------------------------------------------------------
    # Process all categories
    # --------------------------------------------------------

    for category in [
        "acts",
        "cases",
        "rules",
        "sections"
    ]:

        records = process_category(category)

        all_records.extend(records)

    print()
    print("=" * 70)
    print("TOTAL BEFORE VALIDATION")
    print("=" * 70)

    print(
        f"Total records: {len(all_records)}"
    )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("VALIDATING MASTER DATASET")
    print("=" * 70)

    errors = validate(all_records)

    if errors:

        print(
            f"VALIDATION ERRORS: {len(errors)}"
        )

        for error in errors[:20]:
            print(error)

        print()
        print("MASTER DATASET NOT CREATED.")

        return

    print("VALIDATION ERRORS: 0")
    print("MASTER DATASET VALIDATION PASSED")

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    all_records.sort(
        key=lambda x: (
            x["domain"],
            x["type"],
            x["id"]
        )
    )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    type_counts = {}
    domain_counts = {}

    for record in all_records:

        data_type = record["type"]
        domain = record["domain"]

        type_counts[data_type] = (
            type_counts.get(data_type, 0) + 1
        )

        domain_counts[domain] = (
            domain_counts.get(domain, 0) + 1
        )

    # --------------------------------------------------------
    # Save master dataset
    # --------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            all_records,
            f,
            ensure_ascii=False,
            indent=2
        )

    # --------------------------------------------------------
    # Save statistics
    # --------------------------------------------------------

    statistics = {
        "generated_at": datetime.now().isoformat(),
        "total_records": len(all_records),
        "records_by_type": type_counts,
        "records_by_domain": domain_counts,
        "validation_errors": 0
    }

    with open(
        STATS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            statistics,
            f,
            ensure_ascii=False,
            indent=2
        )

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("MASTER DATASET COMPLETE")
    print("=" * 70)

    print(
        f"Total records: {len(all_records)}"
    )

    print()
    print("BY TYPE:")

    for key, value in sorted(
        type_counts.items()
    ):
        print(
            f"  {key:<12}: {value}"
        )

    print()
    print("BY DOMAIN:")

    for key, value in sorted(
        domain_counts.items()
    ):
        print(
            f"  {key:<12}: {value}"
        )

    print()
    print("Output:")
    print(OUTPUT_FILE)

    print()
    print("Statistics:")
    print(STATS_FILE)

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()