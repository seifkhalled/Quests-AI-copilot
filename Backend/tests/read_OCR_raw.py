import os
import base64
import fitz
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")

# Groq vision model — free, fast, 1000 req/day
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

client = Groq(api_key=GROQ_API_KEY)


def pdf_to_base64_images(pdf_path: str, dpi: int = 150) -> list[str]:
    images = []
    doc = fitz.open(pdf_path)
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        images.append(base64.b64encode(pix.tobytes("png")).decode("utf-8"))
    doc.close()
    return images


def extract_single_page(page_num: int, img_b64: str) -> dict:
    """Extract raw text from a single page using Groq."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "Extract all text from this document page exactly as it appears. Preserve the structure and layout."
                        }
                    ]
                }
            ],
            temperature=0,
            max_tokens=4096,
        )

        return {
            "page": page_num,
            "text": response.choices[0].message.content.strip(),
            "success": True
        }

    except Exception as e:
        return {
            "page": page_num,
            "text": "",
            "success": False,
            "error": str(e)
        }


def extract_raw_text_parallel(
    file_path: str,
    max_workers: int = 3,
    delay_between_batches: float = 2.0,
    max_retries: int = 3,
    retry_delay: float = 5.0
) -> dict:

    print(f"Converting {file_path} to images...")
    base64_images = pdf_to_base64_images(file_path, dpi=150)
    total_pages = len(base64_images)
    print(f"Total pages : {total_pages}")
    print(f"Workers     : {max_workers}")
    print(f"Model       : {MODEL}\n")

    page_results = [None] * total_pages

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(extract_single_page, i + 1, img_b64): i
            for i, img_b64 in enumerate(base64_images)
        }

        completed = 0
        for future in as_completed(futures):
            index = futures[future]
            result = future.result()
            page_results[index] = result
            completed += 1

            status = "OK" if result["success"] else "FAILED"
            chars  = len(result["text"])
            print(f"  Page {result['page']:>2} [{status}] — {chars} chars")

            if completed % max_workers == 0 and completed < total_pages:
                print(f"  Waiting {delay_between_batches}s before next batch...")
                time.sleep(delay_between_batches)

    failed_pages = [r["page"] for r in page_results if not r["success"]]
    retry_count = 0

    while failed_pages and retry_count < max_retries:
        retry_count += 1
        print(f"\n🔄 Retry {retry_count}/{max_retries} for {len(failed_pages)} failed pages...")
        time.sleep(retry_delay)

        failed_indices = [r["page"] - 1 for r in page_results if not r["success"]]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(extract_single_page, i + 1, base64_images[i]): i
                for i in failed_indices
            }

            for future in as_completed(futures):
                index = futures[future]
                result = future.result()
                page_results[index] = result

                status = "OK" if result["success"] else "FAILED"
                chars  = len(result["text"])
                print(f"  Page {result['page']:>2} [{status}] — {chars} chars")

                if len([f for f in futures if f.done()]) % max_workers == 0:
                    time.sleep(delay_between_batches)

        failed_pages = [r["page"] for r in page_results if not r["success"]]

    parts = []
    for r in page_results:
        if r["success"]:
            parts.append(f"--- Page {r['page']} ---\n{r['text']}")
        else:
            parts.append(f"--- Page {r['page']} [FAILED: {r.get('error', 'unknown')}] ---")

    final_failed = [r["page"] for r in page_results if not r["success"]]

    return {
        "text":         "\n\n".join(parts),
        "pages":        total_pages,
        "failed_pages": final_failed,
        "page_results": page_results
    }


if __name__ == "__main__":
    pdf_path = r"e:\Prop-Quest\data\quest-79-details.pdf"
    try:
        result = extract_raw_text_parallel(
            pdf_path,
            max_workers=3,
            delay_between_batches=2.0,
            max_retries=3,
            retry_delay=5.0
        )

        print(f"\nPages        : {result['pages']}")
        print(f"Failed pages : {result['failed_pages'] or 'none'}")
        print(f"\n--- FULL EXTRACTED TEXT ---\n")
        print(result["text"])

    except Exception as e:
        print(f"Error: {e}")