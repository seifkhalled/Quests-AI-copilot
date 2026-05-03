import os
import base64
import fitz
import json
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPEN_ROUTER_API_KEY = os.getenv("OPEN_ROUTER_API_KEY")

if not OPEN_ROUTER_API_KEY:
    raise ValueError("OPEN_ROUTER_API_KEY not found in .env")

# Fallback chain — tries each in order
MODELS = [
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-3-27b-it:free",
]

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPEN_ROUTER_API_KEY,
)

def pdf_to_base64_images(pdf_path: str, dpi: int = 150) -> list[str]:
    images = []
    doc = fitz.open(pdf_path)
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        images.append(base64.b64encode(pix.tobytes("png")).decode("utf-8"))
    doc.close()
    return images

PROMPT = """\
You are a structured data extractor for job quest documents.
Extract all information from the document pages above.
Return ONLY a valid JSON object — no markdown, no explanation, no code fences.

{
  "quest_number": <integer or null>,
  "title": "<job title>",
  "company": "<company name>",
  "status": "<Referred|Active|Closed>",
  "location": "<city>",
  "location_type": "<onsite|hybrid|remote>",
  "salary_display": "<salary as written>",
  "salary_min": <number or null>,
  "salary_max": <number or null>,
  "salary_currency": "<EGP|GBP|USD or null>",
  "registration_deadline": "<YYYY-MM-DD or null>",
  "submission_deadline": "<YYYY-MM-DD or null>",
  "role_category": "<frontend|backend|security|ops|design|data|other>",
  "required_skills": ["<skill>"],
  "bonus_skills": ["<skill>"],
  "min_experience_years": <number or null>,
  "max_experience_years": <number or null>,
  "quest_brief": "<main description>",
  "who_we_look_for": ["<requirement>"],
  "mission": "<what the candidate must build or do>",
  "tasks": [{"title": "<title>", "description": "<description>"}],
  "deliverables": ["<deliverable>"],
  "evaluation_criteria": [{"criterion": "<name>", "weight_percent": <number>}],
  "after_submission": "<what happens after>"
}

Use null for any field not present in the document."""


def extract_quest_structured(file_path: str) -> dict:
    print(f"Converting {file_path} to images...")
    base64_images = pdf_to_base64_images(file_path, dpi=150)
    print(f"Pages: {len(base64_images)}")

    content = []
    for img_b64 in base64_images:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"}
        })
    content.append({"type": "text", "text": PROMPT})

    last_error = None
    for model in MODELS:
        try:
            print(f"Trying model: {model}")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": content}],
                temperature=0,
                max_tokens=2048,
                extra_headers={
                    "HTTP-Referer": "https://prop-quest.ai",
                    "X-Title": "Prop-Quest Ingestion",
                }
            )

            raw = response.choices[0].message.content.strip()

            # Strip markdown fences defensively
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1])

            return {
                "data": json.loads(raw),
                "model_used": model
            }

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate" in error_str.lower():
                print(f"  Rate limited on {model}, trying next...")
                time.sleep(2)  # brief pause before next attempt
                last_error = e
                continue
            else:
                # Non-rate-limit error — don't retry
                raise e

    raise RuntimeError(f"All models rate limited. Last error: {last_error}")


if __name__ == "__main__":
    pdf_path = r"e:\Prop-Quest\data\quest-79-details.pdf"
    try:
        result = extract_quest_structured(pdf_path)
        print(f"\nModel used: {result['model_used']}")
        print("\n--- EXTRACTED DATA ---\n")
        print(json.dumps(result["data"], indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")