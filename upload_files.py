"""
upload_files.py
----------------
Developer helper to upload files from `knowledge_base` to OpenAI (assistant/files API).

This script is intended to be run manually. It supports a dry-run mode so you can
inspect what would be uploaded without having an API key present.

Usage:
  python upload_files.py --path knowledge_base --folders wakesurfing_tips.txt tricks.txt --dry-run
  python upload_files.py --upload --path knowledge_base

Notes:
  - Requires OPENAI_API_KEY environment variable (or a .env file) to actually upload.
  - Uses a conservative default rate limit pause between uploads.
"""

from __future__ import annotations

import os
import sys
import time
import argparse
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None

try:
    import openai
except Exception:
    openai = None


def find_files(base: Path, folders: list[str]) -> list[Path]:
    files: list[Path] = []
    for folder in folders:
        candidate = base / folder
        if candidate.is_dir():
            for p in sorted(candidate.iterdir()):
                if p.is_file():
                    files.append(p)
        elif candidate.is_file():
            files.append(candidate)
    return files


def main(argv: list[str] | None = None) -> int:
    if load_dotenv:
        load_dotenv()

    parser = argparse.ArgumentParser(description="Upload knowledge_base files to OpenAI (developer tool)")
    parser.add_argument("--path", default="knowledge_base", help="Base path to knowledge_base")
    parser.add_argument("--folders", nargs="*", default=["wakesurfing_tips.txt", "tricks.txt", "training_methods.pdf"],
                        help="Subfolder names or file names to include")
    parser.add_argument("--upload", action="store_true", help="Perform the actual upload (requires OPENAI_API_KEY)")
    parser.add_argument("--rate", type=float, default=1.0, help="Seconds to wait between uploads")
    args = parser.parse_args(argv)

    base = Path(args.path)
    if not base.exists():
        print(f"⚠️ Base path does not exist: {base}")
        return 2

    targets = find_files(base, args.folders)
    if not targets:
        print("⚠️ No files found for upload.")
        return 0

    print(f"Found {len(targets)} files to consider:")
    for p in targets:
        print(" -", p)

    if not args.upload:
        print("\nDry run: nothing will be uploaded. Rerun with --upload to perform uploads (requires OPENAI_API_KEY).")
        return 0

    if openai is None:
        print("❌ The openai package is not installed. Install with: pip install openai")
        return 3

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY is not set. Set it in the environment or a .env file.")
        return 4

    openai.api_key = api_key

    uploaded_files: list[str] = []
    for p in targets:
        try:
            print(f"Uploading {p}...")
            with p.open("rb") as fh:
                file_obj = openai.files.create(file=fh, purpose="assistants")
            uploaded_files.append(file_obj.id)
            print(f"✅ Uploaded {p.name} -> {file_obj.id}")
        except Exception as exc:
            print(f"❌ Failed to upload {p}: {exc}")
        time.sleep(args.rate)

    if not uploaded_files:
        print("⚠️ No files uploaded (all failed or none provided).")
        return 0

    # create a thread and attach files by default
    try:
        print("Creating thread and attaching files...")
        thread = openai.beta.threads.create()
        thread_id = thread.id
        for i, file_id in enumerate(uploaded_files, start=1):
            try:
                openai.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=f"File {i} of {len(uploaded_files)}: attached for file_search",
                    attachments=[{"file_id": file_id, "tools": [{"type": "file_search"}]}]
                )
                print(f"� Attached {file_id} to thread {thread_id}")
                time.sleep(args.rate)
            except Exception as exc:
                print(f"❌ Failed to attach {file_id}: {exc}")
        print(f"Done. Thread id: {thread_id}")
    except Exception as exc:
        print(f"❌ Failed to create thread or attach files: {exc}")
        return 5

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
