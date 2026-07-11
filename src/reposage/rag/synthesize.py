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

SUMMARY_SYSTEM_INSTRUCTION = """You are analyzing a codebase to produce a concice architecture summary for a developer who has never seen this repo before.

Given a file tree and a sample of representative code, describe:
1. What kind of application this is (web app, CLI tool, API server, library, etc.)
2. The main technologies/frameworks used
3. The high-level architecture (main components and how they likely relate)
4. Any notable patterns (e.g. encryption, external API calls, specific data flows)

Be concise - aim for 150-200 words. Do not describe individual functions in detail; focus on the big picture.
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
        {
            "file_path": r["file_path"],
            "start_line": r["start_line"],
            "end_line": r["end_line"],
            "source_code": r["source_code"],
        }
        for r in results
    ]

    return {
        "answer": answer_text,
        "citations": citations,
        "low_confidence": False,
    }

def select_summary_chunks(all_chunks : list[dict], max_chunks : int = 15) -> list[dict]:

    #prioritize : whole-file chunis (likely docstrings/config) and the largest function-level chunks

    file_level = [c for c in all_chunks if c["symbol_type"] == "file"]
    others = sorted(
        [c for c in all_chunks if c["symbol_type"] != "file"],
        key = lambda c : c ["end_line"] - c["start_line"],
        reverse = True
    )

    selected = file_level + others
    return selected[:max_chunks]

def build_file_tree(all_chunks : list[dict]) -> str:
    paths = sorted({c["file_path"] for c in all_chunks})
    return "\n".join(paths)

def generate_repo_summary(all_chunks : list[dict]) -> str:
    file_tree = build_file_tree(all_chunks)
    sample_chunks = select_summary_chunks(all_chunks)
    sample_text = "\n\n".join(
        f"--- {c['file_path']} ({c['symbol_name']}) ---\n{c['source_code'][:500]}"
        for c in sample_chunks
    )

    prompt = f"File tree:\n{file_tree}\n\nSample code:\n{sample_text}"

    response = client.models.generate_content(
        model = "gemini-2.5-flash",
        contents = prompt,
        config = {"system_instruction" : SUMMARY_SYSTEM_INSTRUCTION}
    )

    return response.text or ""