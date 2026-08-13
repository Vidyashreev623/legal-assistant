import os
import json
from collections import Counter

INPUT_DIR = "processed/sections"

domains = [
    "consumer",
    "contract",
    "cyber",
    "family",
    "property",
    "employment"
]

required_fields = [
    "domain",
    "act",
    "section",
    "title",
    "text",
    "source_file"
]

grand_total = 0
grand_errors = 0


def validate_domain(domain):

    global grand_total, grand_errors

    filename = f"{domain}_sections.json"
    path = os.path.join(INPUT_DIR, filename)

    print("\n" + "=" * 70)
    print(domain.upper())
    print("=" * 70)

    if not os.path.exists(path):
        print("FILE NOT FOUND")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("Total records:", len(data))

    errors = 0
    duplicate_keys = []

    seen = set()

    for i, item in enumerate(data):

        grand_total += 1

        # Required fields
        for field in required_fields:

            if field not in item:
                print(
                    f"Record {i}: missing field '{field}'"
                )
                errors += 1

        # Empty text
        if not str(item.get("text", "")).strip():

            print(
                f"Record {i}: EMPTY TEXT"
            )

            errors += 1

        # Empty section
        if not str(item.get("section", "")).strip():

            print(
                f"Record {i}: EMPTY SECTION"
            )

            errors += 1

        # Duplicate domain + act + section
        key = (
            item.get("domain"),
            item.get("act"),
            item.get("section")
        )

        if key in seen:

            duplicate_keys.append(key)

        seen.add(key)

    if duplicate_keys:

        print(
            "\nDuplicate sections:",
            len(duplicate_keys)
        )

        for key in duplicate_keys[:20]:
            print(" ", key)

        errors += len(duplicate_keys)

    # Text length statistics
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
            round(sum(lengths) / len(lengths), 2),
            "characters"
        )

    print("Errors:", errors)

    grand_errors += errors


for domain in domains:
    validate_domain(domain)


print("\n" + "=" * 70)
print("FINAL VALIDATION")
print("=" * 70)

print("Total records:", grand_total)
print("Total errors:", grand_errors)

if grand_errors == 0:
    print("STATUS: PASS")
else:
    print("STATUS: REVIEW REQUIRED")