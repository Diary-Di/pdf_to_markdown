"""
pdf2md - PDF / XLSX to Markdown converter
Uses pymupdf4llm for PDF -> Markdown, and openpyxl for XLSX -> Markdown tables.
"""

import os
import argparse
from pathlib import Path
import pymupdf4llm
import openpyxl

SUPPORTED_EXTENSIONS = {".pdf", ".xlsx", ".xlsm"}


def _cell_to_str(value) -> str:
    """Render a single cell value as Markdown-table-safe text."""
    if value is None:
        return ""
    text = str(value)
    # Escape pipe characters and collapse newlines so rows stay on one line
    text = text.replace("|", "\\|").replace("\r\n", " ").replace("\n", " ")
    return text.strip()


def convert_xlsx_to_markdown(
    input_path: str,
    output_path: str = None,
    sheet_names: list[str] = None,
) -> str:
    """
    Convert an Excel workbook (.xlsx/.xlsm) to Markdown.

    Each worksheet becomes its own section (## Sheet Name) followed by a
    Markdown table. The first non-empty row of each sheet is treated as
    the table header.

    Args:
        input_path:   Path to the input .xlsx/.xlsm file.
        output_path:  Path to save the .md output (optional).
                      If None, returns the Markdown string only.
        sheet_names:  List of sheet names to convert (None = all sheets).

    Returns:
        Markdown content as a string.
    """
    input_path = Path(input_path).resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Excel file not found: {input_path}")
    if input_path.suffix.lower() not in (".xlsx", ".xlsm"):
        raise ValueError(f"Expected a .xlsx/.xlsm file, got: {input_path.suffix}")

    print(f"[→] Converting: {input_path.name}")
    workbook = openpyxl.load_workbook(str(input_path), data_only=True)

    target_sheets = sheet_names or workbook.sheetnames
    md_parts = []

    for name in target_sheets:
        if name not in workbook.sheetnames:
            print(f"[!] Sheet not found, skipping: {name}")
            continue

        sheet = workbook[name]
        rows = [
            [_cell_to_str(cell) for cell in row]
            for row in sheet.iter_rows(values_only=True)
        ]
        # Drop fully empty trailing/leading rows
        rows = [row for row in rows if any(cell != "" for cell in row)]

        md_parts.append(f"## {name}\n")

        if not rows:
            md_parts.append("_Empty sheet_\n")
            continue

        header, *body_rows = rows
        col_count = len(header)

        md_parts.append("| " + " | ".join(header) + " |")
        md_parts.append("| " + " | ".join(["---"] * col_count) + " |")
        for row in body_rows:
            # Pad/truncate rows to header width so the table stays valid
            row = (row + [""] * col_count)[:col_count]
            md_parts.append("| " + " | ".join(row) + " |")
        md_parts.append("")  # blank line between sheets

    md_text = "\n".join(md_parts).strip() + "\n"

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(md_text, encoding="utf-8")
        print(f"[✓] Saved: {output_path}")

    return md_text


def convert_to_markdown(input_path: str, output_path: str = None, **kwargs) -> str:
    """
    Dispatch to the right converter based on file extension.
    Accepts .pdf (-> convert_pdf_to_markdown) or .xlsx/.xlsm (-> convert_xlsx_to_markdown).
    Extra kwargs are forwarded to the underlying converter (e.g. pages= for PDFs).
    """
    suffix = Path(input_path).suffix.lower()
    if suffix == ".pdf":
        pdf_kwargs = {k: v for k, v in kwargs.items() if k in ("pages", "write_images", "image_dir")}
        return convert_pdf_to_markdown(input_path, output_path, **pdf_kwargs)
    elif suffix in (".xlsx", ".xlsm"):
        xlsx_kwargs = {k: v for k, v in kwargs.items() if k in ("sheet_names",)}
        return convert_xlsx_to_markdown(input_path, output_path, **xlsx_kwargs)
    else:
        raise ValueError(f"Unsupported file type: {suffix} (expected .pdf, .xlsx, or .xlsm)")


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
    Convert all supported files (PDF, XLSX, XLSM) in a directory to Markdown.

    Args:
        input_dir:  Directory containing input files.
        output_dir: Directory to save .md files.
        **kwargs:   Extra options forwarded to the underlying converter
                    (e.g. pages= for PDFs, sheet_names= for XLSX).

    Returns:
        List of output file paths.
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    input_files = sorted(
        p for p in input_dir.iterdir()
        if p.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not input_files:
        print(f"[!] No supported files found in: {input_dir}")
        return []

    results = []
    for src in input_files:
        out = output_dir / (src.stem + ".md")
        convert_to_markdown(str(src), str(out), **kwargs)
        results.append(str(out))

    print(f"\n[✓] Done — {len(results)} file(s) converted.")
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args():
    parser = argparse.ArgumentParser(
        prog="pdf2md",
        description="Convert PDF or XLSX files to Markdown.",
    )
    parser.add_argument("input", help="PDF/XLSX file, or directory of them")
    parser.add_argument(
        "-o", "--output",
        help="Output .md file (single file) or directory (batch mode)",
        default=None,
    )
    parser.add_argument(
        "-p", "--pages",
        help="PDF only: comma-separated 0-based page numbers, e.g. 0,1,4",
        default=None,
    )
    parser.add_argument(
        "--images",
        action="store_true",
        help="PDF only: extract embedded images alongside the Markdown",
    )
    parser.add_argument(
        "-s", "--sheets",
        help="XLSX only: comma-separated sheet names to convert (default: all)",
        default=None,
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    pages = [int(p) for p in args.pages.split(",")] if args.pages else None
    sheet_names = [s.strip() for s in args.sheets.split(",")] if args.sheets else None
    input_path = Path(args.input)

    if input_path.is_dir():
        output_dir = args.output or "output"
        batch_convert(
            str(input_path), output_dir,
            pages=pages, write_images=args.images, sheet_names=sheet_names,
        )
    else:
        suffix = input_path.suffix.lower()
        # Default output: same location, .md extension
        output = args.output or str(input_path.with_suffix(".md"))
        if suffix == ".pdf":
            md = convert_pdf_to_markdown(
                str(input_path), output, pages=pages, write_images=args.images
            )
        elif suffix in (".xlsx", ".xlsm"):
            md = convert_xlsx_to_markdown(str(input_path), output, sheet_names=sheet_names)
        else:
            raise ValueError(f"Unsupported file type: {suffix} (expected .pdf, .xlsx, or .xlsm)")

        if not args.output:
            print("\n--- Preview (first 500 chars) ---")
            print(md[:500])


if __name__ == "__main__":
    main()