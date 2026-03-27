import re
import json
from pathlib import Path


QUESTION_RE = re.compile(r"^(\d+)\.\s+(.*)$")
TYPE_RE = re.compile(r"^Typ:\s+(.*)$")
OPTION_RE = re.compile(r"^([A-E])\.\s+(.*)$") #later A-E can be changed to A-Z too


def clean_line(line: str) -> str:
    return line.strip()


def parse_markdown_exam(md_text: str) -> dict:
    lines = [line.rstrip() for line in md_text.splitlines()]

    exam_title = None
    questions = []
    current_question = None

    for raw_line in lines:
        line = clean_line(raw_line)

        if not line:
            continue

        if exam_title is None and line.startswith("Klausur "):
            exam_title = line

        if line == "--":
            continue

        if line.startswith("Titel:"):
            continue

        q_match = QUESTION_RE.match(line)
        if q_match:
            if current_question is not None:
                questions.append(current_question)

            q_number = int(q_match.group(1))
            q_text = q_match.group(2).strip()

            current_question = {
                "id": f"q{q_number}",
                "number": q_number,
                "type": None,
                "text": q_text,
                "options": {},
                "correct_options": [],
                "raw_block": [line]
            }
            continue

        if current_question is None:
            continue

        current_question["raw_block"].append(line)

        type_match = TYPE_RE.match(line)
        if type_match:
            current_question["type"] = type_match.group(1).strip()
            continue

        is_bold = line.startswith("**") and line.endswith("**")
        normalized_line = line.replace("**", "").strip()

        option_match = OPTION_RE.match(normalized_line)
        if option_match:
            option_letter = option_match.group(1).strip()
            option_text = option_match.group(2).strip()

            current_question["options"][option_letter] = option_text

            if is_bold:
                current_question["correct_options"].append(option_letter)

            continue

    if current_question is not None:
        questions.append(current_question)

    for q in questions:
        q["raw_block"] = "\n".join(q["raw_block"])

    return {
        "exam_title": exam_title,
        "questions": questions
    }


def main():
    input_path = input("Enter path to .md file: ").strip().strip('"')
    md_file = Path(input_path)

    if not md_file.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_file}")

    md_text = md_file.read_text(encoding="utf-8")
    parsed = parse_markdown_exam(md_text)

    output_path = md_file.with_name(md_file.stem + "_parsed.json")
    output_path.write_text(
        json.dumps(parsed, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"Parsed {len(parsed['questions'])} questions.")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()