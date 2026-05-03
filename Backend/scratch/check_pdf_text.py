import fitz
import sys

def check_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        if text.strip():
            print(f"TEXT_FOUND: {len(text)} characters")
            print("SAMPLE:")
            print(text[:500])
        else:
            print("NO_TEXT_FOUND (Image-based PDF)")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    check_pdf(sys.argv[1])
