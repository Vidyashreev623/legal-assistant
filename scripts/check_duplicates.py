from pathlib import Path
import hashlib

CASES_DIR = Path("dataset/consumer/cases")


def file_hash(path):
    hasher = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def main():
    pdf_files = list(CASES_DIR.rglob("*.pdf")) + list(CASES_DIR.rglob("*.PDF"))

    print(f"Total PDFs found: {len(pdf_files)}")

    hash_groups = {}

    for pdf in pdf_files:
        try:
            file_hash_value = file_hash(pdf)

            if file_hash_value not in hash_groups:
                hash_groups[file_hash_value] = []

            hash_groups[file_hash_value].append(pdf)

        except Exception as e:
            print(f"ERROR: {pdf}")
            print(e)

    duplicate_groups = [
        files for files in hash_groups.values()
        if len(files) > 1
    ]

    print(f"Unique PDF contents: {len(hash_groups)}")
    print(f"Duplicate groups: {len(duplicate_groups)}")

    print("\n===== DUPLICATE GROUPS =====")

    for number, group in enumerate(duplicate_groups, start=1):

        print(f"\n--- Group {number} ---")

        for file in group:
            print(file)


if __name__ == "__main__":
    main()