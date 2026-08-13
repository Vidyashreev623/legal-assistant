import os
import json


INPUT_DIR = "processed/rules"

DOMAINS = [
    "consumer",
    "contract",
    "cyber",
    "family",
    "property",
    "employment"
]

required_fields = [
    "domain",
    "document_type",
    "title",
    "text",
    "source_file"
]

total_records = 0
total_errors = 0


def validate_domain(domain):

    global total_records
    global total_errors

    filename = f"{domain}_rules.json"

    path = os.path.join(
        INPUT_DIR,
        filename
    )

    print("\n" + "=" * 70)
    print(domain.upper())
    print("=" * 70)

    if not os.path.exists(path):

        print("FILE NOT FOUND")

        return

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    print(
        "Total records:",
        len(data)
    )

    errors = 0

    seen_files = set()

    for index, item in enumerate(data):

        total_records += 1

        # ----------------------------------------------------
        # Required fields
        # ----------------------------------------------------

        for field in required_fields:

            if field not in item:

                print(
                    f"Record {index}: "
                    f"missing field '{field}'"
                )

                errors += 1

        # ----------------------------------------------------
        # Empty text
        # ----------------------------------------------------

        text = str(
            item.get("text", "")
        ).strip()

        if not text:

            print(
                f"Record {index}: EMPTY TEXT"
            )

            errors += 1

        # ----------------------------------------------------
        # Empty source file
        # ----------------------------------------------------

        source = str(
            item.get("source_file", "")
        ).strip()

        if not source:

            print(
                f"Record {index}: "
                "EMPTY SOURCE FILE"
            )

            errors += 1

        # ----------------------------------------------------
        # Duplicate source files
        # ----------------------------------------------------

        if source in seen_files:

            print(
                f"Record {index}: "
                f"DUPLICATE SOURCE FILE: {source}"
            )

            errors += 1

        seen_files.add(source)

    # --------------------------------------------------------
    # Text statistics
    # --------------------------------------------------------

    lengths = [
        len(str(item.get("text", "")))
        for item in data
    ]

    if lengths:

        print(
            "Shortest text:",
            min(lengths),
            "characters"
        )

        print(
            "Longest text:",
            max(lengths),
            "characters"
        )

        print(
            "Average text:",
            round(
                sum(lengths) / len(lengths),
                2
            ),
            "characters"
        )

    print(
        "Errors:",
        errors
    )

    total_errors += errors


# ============================================================
# RUN
# ============================================================

for domain in DOMAINS:

    validate_domain(domain)


print("\n" + "=" * 70)
print("FINAL RULE VALIDATION")
print("=" * 70)

print(
    "Total records:",
    total_records
)

print(
    "Total errors:",
    total_errors
)

if total_errors == 0:

    print(
        "STATUS: PASS"
    )

else:

    print(
        "STATUS: REVIEW REQUIRED"
    )