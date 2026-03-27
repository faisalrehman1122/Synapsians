"""
Converts annotated PDF exam files into OpenAI fine-tuning JSONL format.

These PDFs were exported from Word with "Track Changes / Print All Markup",
so expert comments appear as inline text like:
    Commented [EA1]: Some feedback here...
    Deleted: old text

The script:
1. Extracts full text from each PDF.
2. Splits by "--" to get individual questions (same delimiter used in the app).
3. Parses inline "Commented [...]:" lines as expert feedback for each question.
4. Pairs each question with its system prompt + expert comments as the assistant response.
5. Outputs training.jsonl and validation.jsonl.
"""

import os
import re
import json
import fitz  # PyMuPDF

# ── Import the system prompt builder from the existing engine ──
import sys
sys.path.insert(0, os.path.dirname(__file__))
from llm_engine import build_system_prompt

# ── Paths ──
PDF_DIR  = os.path.join(os.path.dirname(__file__), "..", "data", "ft_dataset_pdf")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "..", "data", "ft_data2")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Train / Validation split (80/20) ──
TRAINING_FILES = [
    "Klausurvorlage_MIII_0226_Korrektur.pdf",
    "Klausurvorlage_Orthopädie_WiSe2526_AE.pdf",
    "Klausurvorlage_Gynäkologie_WiSe2526_AE.pdf",
    "InterdisziplinäresWissen_und_Handeln WiSe 2025_26_AE.pdf",
]
VALIDATION_FILES = [
    "Klausurvorlage_Klin_Chemie_WiSe2526_AE.pdf",
    "Klausurvorlage_Pathologie_HM_WiSe2526_AE.pdf",
]

# Regex to capture inline comments printed by Word markup export
# Matches lines like:  Commented [EA1]: This is the feedback text
COMMENT_RE = re.compile(r"^Commented\s*\[.*?\]:\s*(.+)", re.MULTILINE)
# Matches lines like:  Deleted: Kprim
DELETED_RE = re.compile(r"^Deleted:\s*(.+)", re.MULTILINE)


def extract_full_text(pdf_path: str) -> str:
    """Extract all text from a PDF, page by page."""
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pages.append(page.get_text("text"))
    doc.close()
    return "\n".join(pages)


def detect_question_type(block: str) -> str:
    """Try to find the question type from a 'Typ: ...' line inside the block."""
    m = re.search(r"Typ:\s*(\S+)", block)
    if m:
        t = m.group(1).strip()
        if "PickS" in t:
            return "PickS"
        if "Kprim" in t:
            return "Kprim"
        if "TypA" in t:
            return "TypA"
    return "TypA"  # default


def extract_comments_from_block(block: str) -> list[dict]:
    """
    Pull out expert comments and deletions from a question block.
    Returns a list of {"exact_quote": ..., "comment": ...} dicts.
    """
    feedback = []

    # Gather "Commented [EAx]: ..." entries
    for m in COMMENT_RE.finditer(block):
        comment_text = m.group(1).strip()
        if comment_text:
            feedback.append({
                "exact_quote": "",  # will try to match below
                "comment": comment_text,
            })

    # Gather "Deleted: ..." entries  — these indicate tracked deletions
    for m in DELETED_RE.finditer(block):
        deleted_text = m.group(1).strip()
        if deleted_text:
            feedback.append({
                "exact_quote": deleted_text,
                "comment": f"Geloeschter Text: {deleted_text} - wurde entfernt.",
            })

    return feedback


def clean_question_block(block: str) -> str:
    """
    Remove the inline comment / deleted lines from the question text
    so the 'user' prompt only contains the actual question content.
    Also strip trailing "Titel: ..." lines that are just metadata.
    """
    lines = block.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if COMMENT_RE.match(stripped):
            continue
        if DELETED_RE.match(stripped):
            continue
        if stripped.startswith("Titel:"):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def process_pdf(pdf_path: str) -> list[dict]:
    """
    Process a single PDF → list of JSONL-ready message dicts.
    """
    full_text = extract_full_text(pdf_path)
    raw_blocks = full_text.split("--")

    entries = []
    for idx, block in enumerate(raw_blocks):
        block = block.strip()
        if not block:
            continue

        # Skip header / metadata-only blocks (no question number pattern)
        if not re.search(r"\d+\.\s", block):
            continue

        question_type = detect_question_type(block)
        comments = extract_comments_from_block(block)
        clean_text = clean_question_block(block)

        if not clean_text:
            continue

        # Build the assistant response JSON
        assistant_json = {
            "feedback_comments": comments,
            "general_feedback": "Keine weiteren strukturellen Anmerkungen." if not comments else ""
        }

        system_prompt = build_system_prompt(question_type)

        entry = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": clean_text},
                {"role": "assistant", "content": json.dumps(assistant_json, ensure_ascii=False)},
            ]
        }
        entries.append(entry)

    return entries


def create_jsonl(files: list[str], output_filename: str):
    all_entries = []
    for fname in files:
        fpath = os.path.join(PDF_DIR, fname)
        if not os.path.exists(fpath):
            print(f"⚠  File not found, skipping: {fname}")
            continue
        print(f"  Extracting: {fname}")
        entries = process_pdf(fpath)
        print(f"    → {len(entries)} questions with {sum(len(e['messages'][2]['content']) > 50 for e in entries)} commented")
        all_entries.extend(entries)

    out_path = os.path.join(OUT_DIR, output_filename)
    with open(out_path, "w", encoding="utf-8") as f:
        for entry in all_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"  ✅ Saved {len(all_entries)} entries to {out_path}\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Generating Training Data…")
    print("=" * 60)
    create_jsonl(TRAINING_FILES, "training.jsonl")

    print("=" * 60)
    print("Generating Validation Data…")
    print("=" * 60)
    create_jsonl(VALIDATION_FILES, "validation.jsonl")

    print("Done! Files saved to data/ft_data2/")
