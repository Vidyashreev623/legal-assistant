import os
import json
import re


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
    "sections"
)


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):
    """
    Clean common PDF/text extraction artifacts.

    Does NOT remove legal content.
    """

    if text is None:
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

    # Normalize line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove trailing spaces
    text = re.sub(
        r"[ \t]+$",
        "",
        text,
        flags=re.MULTILINE
    )

    # Remove excessive blank lines
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# JSON SECTION PROCESSING
# ============================================================

def process_json_file(path, domain, folder_act_name):
    """
    Process an existing JSON section file.

    IMPORTANT:
    The Act name from the original JSON is preserved.
    """

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

    except Exception as e:

        print(f"ERROR reading JSON: {path}")
        print(f"Reason: {e}")

        return []

    # JSON may contain either:
    #
    # [
    #   {...},
    #   {...}
    # ]
    #
    # OR:
    #
    # {
    #   ...
    # }

    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list):

        print(
            f"WARNING: Unexpected JSON structure: {path}"
        )

        return []

    results = []

    for item in data:

        if not isinstance(item, dict):
            continue

        # ----------------------------------------------------
        # Preserve original Act name
        # ----------------------------------------------------

        act = (
            item.get("act")
            or item.get("act_name")
            or item.get("act_title")
            or item.get("Act")
            or folder_act_name
        )

        # ----------------------------------------------------
        # Section number
        # ----------------------------------------------------

        section = (
            item.get("section")
            or item.get("section_number")
            or item.get("number")
            or item.get("Section")
        )

        # ----------------------------------------------------
        # Section title
        # ----------------------------------------------------

        title = (
            item.get("title")
            or item.get("heading")
            or item.get("section_title")
            or ""
        )

        # ----------------------------------------------------
        # Section text
        # ----------------------------------------------------

        text = (
            item.get("text")
            or item.get("content")
            or item.get("body")
            or item.get("section_text")
        )

        # Skip unusable records
        if section is None:
            continue

        if text is None:
            continue

        text = clean_text(text)

        if not text:
            continue

        results.append({

            "domain": domain,

            "act": clean_text(act),

            "section": str(section).strip(),

            "title": clean_text(title),

            "text": text,

            "source_file": os.path.basename(path)

        })

    return results


# ============================================================
# TXT SECTION PROCESSING
# ============================================================

def process_txt_file(path, domain, folder_act_name):
    """
    Process Contract-style TXT section files.

    Example:

    Act: contract act
    Section: 10
    ==========================

    10. What agreements are contracts...
    """

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
            errors="replace"
        ) as f:

            raw = f.read()

    except Exception as e:

        print(f"ERROR reading TXT: {path}")
        print(f"Reason: {e}")

        return None

    raw = clean_text(raw)

    # --------------------------------------------------------
    # Extract Act
    # --------------------------------------------------------

    act_match = re.search(
        r"^Act:\s*(.+)$",
        raw,
        flags=re.MULTILINE | re.IGNORECASE
    )

    if act_match:

        act = act_match.group(1).strip()

    else:

        act = folder_act_name

    # --------------------------------------------------------
    # Extract Section
    # --------------------------------------------------------

    section_match = re.search(
        r"^Section:\s*([0-9]+[A-Z]?)\s*$",
        raw,
        flags=re.MULTILINE | re.IGNORECASE
    )

    if not section_match:

        print(
            f"WARNING: Section number not found: {path}"
        )

        return None

    section = section_match.group(1).strip()

    # --------------------------------------------------------
    # Remove metadata/header
    # --------------------------------------------------------

    text = re.sub(
        r"^Act:.*?\n",
        "",
        raw,
        count=1,
        flags=re.MULTILINE | re.IGNORECASE
    )

    text = re.sub(
        r"^Section:.*?\n",
        "",
        text,
        count=1,
        flags=re.MULTILINE | re.IGNORECASE
    )

    text = re.sub(
        r"^=+\s*\n",
        "",
        text,
        count=1
    )

    text = clean_text(text)

    if not text:
        return None

    # --------------------------------------------------------
    # Try to extract title
    # --------------------------------------------------------

    title = ""

    title_pattern = re.compile(
        rf"^\s*{re.escape(section)}\.\s*(.+?)(?:\s*[—–-]\s*|\n|$)",
        flags=re.MULTILINE
    )

    title_match = title_pattern.search(text)

    if title_match:

        title = title_match.group(1).strip()

    return {

        "domain": domain,

        "act": clean_text(act),

        "section": section,

        "title": clean_text(title),

        "text": text,

        "source_file": os.path.basename(path)

    }


# ============================================================
# PROCESS ONE DOMAIN
# ============================================================

def process_domain(domain):

    section_dir = os.path.join(
        DATASET_DIR,
        domain,
        "sections"
    )

    if not os.path.exists(section_dir):

        print(
            f"[SKIP] Sections folder not found: {section_dir}"
        )

        return []

    results = []

    # --------------------------------------------------------
    # Walk through all Act folders/files
    # --------------------------------------------------------

    for root, dirs, files in os.walk(section_dir):

        relative_path = os.path.relpath(
            root,
            section_dir
        )

        # If sections are directly inside sections/
        if relative_path == ".":

            folder_act_name = domain

        else:

            folder_act_name = relative_path.replace(
                "\\",
                "/"
            )

        for filename in sorted(files):

            path = os.path.join(
                root,
                filename
            )

            # ------------------------------------------------
            # JSON
            # ------------------------------------------------

            if filename.lower().endswith(".json"):

                items = process_json_file(
                    path,
                    domain,
                    folder_act_name
                )

                results.extend(items)

            # ------------------------------------------------
            # TXT
            # ------------------------------------------------

            elif filename.lower().endswith(".txt"):

                item = process_txt_file(
                    path,
                    domain,
                    folder_act_name
                )

                if item:

                    results.append(item)

    return results


# ============================================================
# SORTING
# ============================================================

def section_sort_key(item):

    section = str(
        item.get("section", "")
    ).strip()

    # Examples:
    #
    # 1
    # 10
    # 14A
    # 20B

    match = re.match(
        r"^(\d+)([A-Z]*)$",
        section,
        flags=re.IGNORECASE
    )

    if match:

        number = int(
            match.group(1)
        )

        suffix = match.group(2).upper()

        return (
            number,
            suffix
        )

    return (
        999999,
        section
    )


# ============================================================
# MAIN PROCESSING
# ============================================================

def main():

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    grand_total = 0

    print("=" * 70)
    print("LEGAL ASSISTANT - SECTION PROCESSING")
    print("=" * 70)

    for domain in DOMAINS:

        print("\n")
        print("=" * 70)
        print(f"PROCESSING: {domain.upper()}")
        print("=" * 70)

        sections = process_domain(
            domain
        )

        # Sort sections
        sections.sort(
            key=lambda x: (
                x.get("act", ""),
                section_sort_key(x)
            )
        )

        output_file = os.path.join(
            OUTPUT_DIR,
            f"{domain}_sections.json"
        )

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
            f"Sections processed: {len(sections)}"
        )

        print(
            f"Output: {output_file}"
        )

        grand_total += len(
            sections
        )

    print("\n")
    print("=" * 70)
    print("PROCESSING COMPLETE")
    print("=" * 70)

    print(
        f"TOTAL SECTIONS: {grand_total}"
    )

    print("=" * 70)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()