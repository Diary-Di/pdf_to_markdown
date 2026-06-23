"""
pdf2md - PDF to Markdown converter
Uses pymupdf4llm for high-quality Markdown output.
"""

import os
import argparse
from pathlib import Path
import pymupdf4llm


def convert_pdf_to_markdown(
    input_path: str,
    output_path: str = None,
    pages: list[int] = None,
    write_images: bool = False,
    image_dir: str = None,
) -> str:
    """
    Convert a PDF file to Markdown.

    Args:
        input_path:   Path to the input PDF file.
        output_path:  Path to save the .md output (optional).
                      If None, returns the Markdown string only.
        pages:        List of 0-based page indices to convert (None = all pages).
        write_images: Extract embedded images to disk alongside the Markdown.
        image_dir:    Directory to save extracted images (defaults to output dir).

    Returns:
        Markdown content as a string.
    """
    input_path = Path(input_path).resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"PDF not found: {input_path}")
    if input_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {input_path.suffix}")

    # Build kwargs for pymupdf4llm
    kwargs = {}
    if pages is not None:
        kwargs["pages"] = pages
    if write_images:
        img_output = image_dir or (Path(output_path).parent if output_path else Path.cwd())
        kwargs["write_images"] = True
        kwargs["image_path"] = str(img_output)

    print(f"[→] Converting: {input_path.name}")
    md_text = pymupdf4llm.to_markdown(str(input_path), **kwargs)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(md_text, encoding="utf-8")
        print(f"[✓] Saved: {output_path}")

    return md_text


def batch_convert(input_dir: str, output_dir: str, **kwargs) -> list[str]:
    """
    Convert all PDF files in a directory to Markdown.

    Args:
        input_dir:  Directory containing PDF files.
        output_dir: Directory to save .md files.
        **kwargs:   Extra options forwarded to convert_pdf_to_markdown().

    Returns:
        List of output file paths.
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    pdf_files = list(input_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"[!] No PDF files found in: {input_dir}")
        return []

    results = []
    for pdf in pdf_files:
        out = output_dir / (pdf.stem + ".md")
        convert_pdf_to_markdown(str(pdf), str(out), **kwargs)
        results.append(str(out))

    print(f"\n[✓] Done — {len(results)} file(s) converted.")
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args():
    parser = argparse.ArgumentParser(
        prog="pdf2md",
        description="Convert PDF files to Markdown using pymupdf4llm.",
    )
    parser.add_argument("input", help="PDF file or directory of PDFs")
    parser.add_argument(
        "-o", "--output",
        help="Output .md file (single file) or directory (batch mode)",
        default=None,
    )
    parser.add_argument(
        "-p", "--pages",
        help="Comma-separated 0-based page numbers, e.g. 0,1,4",
        default=None,
    )
    parser.add_argument(
        "--images",
        action="store_true",
        help="Extract embedded images alongside the Markdown",
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    pages = [int(p) for p in args.pages.split(",")] if args.pages else None
    input_path = Path(args.input)

    if input_path.is_dir():
        output_dir = args.output or "output"
        batch_convert(str(input_path), output_dir, pages=pages, write_images=args.images)
    else:
        # Default output: same location, .md extension
        output = args.output or str(input_path.with_suffix(".md"))
        md = convert_pdf_to_markdown(
            str(input_path), output, pages=pages, write_images=args.images
        )
        if not args.output:
            print("\n--- Preview (first 500 chars) ---")
            print(md[:500])


if __name__ == "__main__":
    main()