"""CLI entrypoint for the PHP/WAMP bridge: PDF path in → ZIP path out."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from receipt_splitter import process_pdf


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({"error": "Uso: split_cli.py <entrada.pdf> <saida.zip>"}), file=sys.stderr)
        return 2

    pdf_path = Path(sys.argv[1])
    zip_path = Path(sys.argv[2])

    try:
        zip_bytes, count = process_pdf(pdf_path.read_bytes())
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1

    zip_path.write_bytes(zip_bytes)
    print(json.dumps({"count": count}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
