"""SmartScanner — web app to split scanned receipt PDFs."""

from __future__ import annotations

import re
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file
import io

from receipt_splitter import process_pdf

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 40 * 1024 * 1024  # 40 MB


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/split")
def split_pdf():
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado."}), 400

    upload = request.files["file"]
    if not upload or not upload.filename:
        return jsonify({"error": "Selecione um arquivo PDF."}), 400

    filename = upload.filename.lower()
    if not filename.endswith(".pdf"):
        return jsonify({"error": "Envie um arquivo PDF."}), 400

    pdf_bytes = upload.read()
    if not pdf_bytes:
        return jsonify({"error": "Arquivo vazio."}), 400

    try:
        zip_bytes, count = process_pdf(pdf_bytes)
    except Exception as exc:  # noqa: BLE001 — surface message to user
        return jsonify({"error": f"Falha ao processar o PDF: {exc}"}), 500

    if count == 0:
        return jsonify({"error": "Nenhum recibo encontrado no PDF."}), 422

    stem = Path(upload.filename).stem
    stem = re.sub(r"[^\w\-]+", "_", stem, flags=re.UNICODE).strip("_") or "recibos"
    download_name = f"{stem}_recibos.zip"

    return send_file(
        io.BytesIO(zip_bytes),
        mimetype="application/zip",
        as_attachment=True,
        download_name=download_name,
    )


@app.get("/api/health")
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
