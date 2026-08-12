from pathlib import Path
from pypdf import PdfReader

pdf_path = Path(
    "dataset/consumer/acts/consumer act 2019.pdf"
)

reader = PdfReader(str(pdf_path))

print("Number of pages:", len(reader.pages))

text = ""

for page_number, page in enumerate(reader.pages, start=1):
    page_text = page.extract_text()

    if page_text:
        text += f"\n\n--- PAGE {page_number} ---\n\n"
        text += page_text

print("\nExtracted characters:", len(text))

print("\n========== SAMPLE ==========\n")
print(text[:5000])