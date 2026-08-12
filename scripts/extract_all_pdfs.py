from pathlib import Path
import pymupdf

BASE_DIR = Path("dataset/consumer")

FOLDERS = {
    "ACTS": BASE_DIR / "acts",
    "RULES": BASE_DIR / "rules",
    "REGULATIONS": BASE_DIR / "regulations",
    "CASES": BASE_DIR / "cases",
}


def extract_pdf(pdf_path):
    """Extract all text from a PDF."""
    try:
        doc = pymupdf.open(pdf_path)

        text = ""

        for page in doc:
            text += page.get_text()

        doc.close()

        return text.strip()

    except Exception as e:
        print(f"ERROR: {pdf_path.name} -> {e}")
        return None


def process_folder(name, folder):
    print(f"\n===== {name} =====")

    if not folder.exists():
        print(f"Folder not found: {folder}")
        return

    pdf_files = list(folder.rglob("*.pdf")) + list(folder.rglob("*.PDF"))

    print(f"PDF files found: {len(pdf_files)}")

    # Create extracted folder
    output_folder = folder / "extracted"
    output_folder.mkdir(exist_ok=True)

    for pdf_path in pdf_files:

        text = extract_pdf(pdf_path)

        if text is None:
            continue

        # Same filename but .txt
        txt_name = pdf_path.stem + ".txt"
        txt_path = output_folder / txt_name

        txt_path.write_text(text, encoding="utf-8")

        print(
            f"OK: {pdf_path.name} "
            f"-> {len(text):,} characters "
            f"-> {txt_path.name}"
        )


def main():

    for name, folder in FOLDERS.items():
        process_folder(name, folder)

    print("\n===== EXTRACTION COMPLETE =====")


if __name__ == "__main__":
    main()