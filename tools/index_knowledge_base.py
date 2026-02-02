"""Simple CLI for indexing Safari/Challenge documents into SQLite."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Tuple

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOC_ROOT = ROOT / "knowledge_base"
DB_PATH = ROOT / "knowledge_base.db"
REQUIRED_COLUMNS = (
    "CREATE TABLE IF NOT EXISTS kb_documents (\n"
    "id TEXT PRIMARY KEY,\n"
    "path TEXT NOT NULL,\n"
    "type TEXT NOT NULL,\n"
    "title TEXT,\n"
    "content TEXT,\n"
    "metadata TEXT,\n"
    "updated_at TEXT\n"
    ")"
)


def parse_document(path: Path) -> Tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    metadata: dict = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            meta_block = parts[1].strip()
            body = parts[2].strip()
            metadata = yaml.safe_load(meta_block) or {}
    return metadata, body


def index_domain(domain: str | None):
    docs = []
    for subdir in DOC_ROOT.iterdir():
        if subdir.is_file():
            continue
        if domain and subdir.name != domain:
            continue
        for file_path in subdir.rglob("*"):
            if file_path.suffix.lower() not in {".md", ".txt"}:
                continue
            metadata, content = parse_document(file_path)
            doc_type = subdir.name
            docs.append((file_path, doc_type, metadata, content))
    if not docs:
        print("No documents found for domain", domain)
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(REQUIRED_COLUMNS)
        for file_path, doc_type, metadata, content in docs:
            doc_id = f"{doc_type}:{file_path.stem}"
            conn.execute(
                "REPLACE INTO kb_documents (id, path, type, title, content, metadata, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    doc_id,
                    str(file_path.relative_to(ROOT)),
                    doc_type,
                    metadata.get("title")
                    or metadata.get("showcase_id")
                    or file_path.stem,
                    content,
                    json.dumps(metadata, ensure_ascii=False),
                    datetime.utcnow().isoformat(),
                ),
            )
        conn.commit()
        print(f"Indexed {len(docs)} documents into {DB_PATH}")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Index knowledge base files with metadata front matter"
    )
    parser.add_argument(
        "--domain", choices=["safari", "challenge", "faq"], default=None
    )
    args = parser.parse_args()
    index_domain(args.domain)


if __name__ == "__main__":
    main()
