from pathlib import Path
import mammoth
from markdownify import markdownify as md


def convert_docx_to_markdown(input_path: str, output_path = None):
    input_file = Path(input_path)

    if not input_file.exists():
        raise FileNotFoundError(f"File not found: {input_file}")

    with input_file.open("rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        html = result.value

    markdown = md(html)

    if output_path is None:
        output_file = input_file.with_suffix(".md")
    else:
        output_file = Path(output_path)

    output_file.write_text(markdown, encoding="utf-8")

    print(f"Markdown saved to: {output_file}")


if __name__ == "__main__":
    path = input("Enter path to .docx file: ").strip().strip('"')
    convert_docx_to_markdown(path)