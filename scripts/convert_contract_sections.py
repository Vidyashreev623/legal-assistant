import os
import re
import json

INPUT_DIR = "dataset/contract/sections"
OUTPUT_DIR = "dataset/contract/sections_json"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_encoding(text):
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

    return text


def read_section_file(path):

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    text = clean_encoding(text)

    # Extract Act
    act_match = re.search(
        r"Act:\s*(.+)",
        text
    )

    # Extract Section
    section_match = re.search(
        r"Section:\s*([0-9]+[A-Z]?)",
        text
    )

    if not act_match or not section_match:
        return None

    act = act_match.group(1).strip()
    section = section_match.group(1).strip()

    # Remove metadata/header
    body = re.sub(
        r"^Act:.*?\n",
        "",
        text,
        count=1
    )

    body = re.sub(
        r"^Section:.*?\n",
        "",
        body,
        count=1
    )

    body = re.sub(
        r"^=+\s*\n",
        "",
        body,
        count=1
    )

    body = body.strip()

    # Try to extract section title
    title = ""

    title_match = re.search(
        rf"^{re.escape(section)}\.\s*(.*?)(?:\s*[—-]\s*|\n)",
        body
    )

    if title_match:
        title = title_match.group(1).strip()

    # Clean whitespace
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r"\n{3,}", "\n\n", body)

    return {
        "domain": "contract",
        "source_type": "act_section",
        "act": act,
        "section": section,
        "title": title,
        "text": body,
        "source_file": os.path.basename(path)
    }


def process_all_sections():

    total = 0
    failed = 0

    for act_folder in os.listdir(INPUT_DIR):

        act_path = os.path.join(
            INPUT_DIR,
            act_folder
        )

        if not os.path.isdir(act_path):
            continue

        output_file = os.path.join(
            OUTPUT_DIR,
            f"{act_folder}.json"
        )

        sections = []

        for filename in os.listdir(act_path):

            if not filename.lower().endswith(".txt"):
                continue

            file_path = os.path.join(
                act_path,
                filename
            )

            result = read_section_file(file_path)

            if result:

                sections.append(result)
                total += 1

            else:

                print(
                    "Could not process:",
                    file_path
                )

                failed += 1

        # Sort sections naturally
        def section_sort(item):
            number = item["section"]
            match = re.match(r"(\d+)([A-Z]*)", number)

            if match:
                return (
                    int(match.group(1)),
                    match.group(2)
                )

            return (999999, "")

        sections.sort(key=section_sort)

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                sections,
                f,
                ensure_ascii=False,
                indent=2
            )

        print(
            f"{act_folder}: {len(sections)} sections → {output_file}"
        )

    print("\n" + "=" * 60)
    print("TOTAL SECTIONS:", total)
    print("FAILED:", failed)
    print("=" * 60)


if __name__ == "__main__":
    process_all_sections()