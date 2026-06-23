"""
pdf2md Web App — Flask backend
"""

import os
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_file
import pymupdf4llm

app = Flask(__name__)

UPLOAD_FOLDER = Path("uploads")
OUTPUT_FOLDER = Path("output")
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():
    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400

    file = request.files["file"]

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported."}), 400

    # Save uploaded file with a unique name
    uid = uuid.uuid4().hex
    input_path = UPLOAD_FOLDER / f"{uid}.pdf"
    output_path = OUTPUT_FOLDER / f"{uid}.md"
    original_stem = Path(file.filename).stem

    file.save(str(input_path))

    try:
        md_text = pymupdf4llm.to_markdown(str(input_path))
        output_path.write_text(md_text, encoding="utf-8")
    except Exception as e:
        return jsonify({"error": f"Conversion failed: {str(e)}"}), 500
    finally:
        input_path.unlink(missing_ok=True)  # clean up upload

    word_count = len(md_text.split())
    line_count = md_text.count("\n")
    preview = md_text[:1200]

    return jsonify({
        "uid": uid,
        "filename": original_stem + ".md",
        "preview": preview,
        "word_count": word_count,
        "line_count": line_count,
        "char_count": len(md_text),
    })


@app.route("/download/<uid>")
def download(uid):
    # Sanitize uid — only hex chars allowed
    uid = "".join(c for c in uid if c in "0123456789abcdef")
    output_path = OUTPUT_FOLDER / f"{uid}.md"
    if not output_path.exists():
        return jsonify({"error": "File not found."}), 404

    filename = request.args.get("name", "converted.md")
    return send_file(str(output_path), as_attachment=True, download_name=filename)


if __name__ == "__main__":
    app.run(debug=True, port=5000)