import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

SYSTEM_INSTRUCTION = """You are a codebase assistant. You answer questions about a codebase using ONLY the code snippest provided to you below - never from general knowledge or similar open-source projects.

Rules :
1. Every factual claim about the code must end with a citation in the exact format (file_path : start_line-end_line).
2. If the provided snippets don't contain enough information to answer confidently, say so explicitly instead of guessing.
3. If the question requires information from multiple snippets, synthesize across all of them - don't just describe the first one.
4. Be concise. Do no repeat the code verbatim at length; describe what it does.
"""

CONFIDENCE_THRESHOLD = 0.75


def build_context_block(results : list[dict]) -> str :
    blocks = []

    for r in results :
        location = f"{r['file_path']} : {r['start_line']}-{r['end_line']}"
        blocks.append(f"--- {location} ({r["symbol_name"]}) ---\n{r['source_code']}")

    return "\n\n".join(blocks)

def is_low_confidence(results : list[dict]) -> bool :
    if not results:
        return True

    return results[0]["distance"] > CONFIDENCE_THRESHOLD


def synthesize_answer(question : str, results : list[dict]) -> dict :
    if is_low_confidence(results):
        return {
            "answer" : "I don't have enough relevant context in this codebase to answer that confidently",
            "citations" : [],
            "low_confidence" : True
        }

    context = build_context_block(results)
    prompt = f"Question : {question}\n\nCode context : \n{context}\n\nAnswer the question using only the context above."

    response = client.models.generate_content(
        model = "gemini-2.5-flash",
        contents = prompt,
        config = {"system_instruction" : SYSTEM_INSTRUCTION}
    )

    answer_text = response.text
    citations = [
        f"{r['file_path']}:{r['start_line']}-{r['end_line']}" for r in results
    ]

    return {
        "answer": answer_text,
        "citations": citations,
        "low_confidence": False,
    }