"""
Запуск scripts/blog_raw_feed_smoke_check.py и форматирование отчёта для Telegram.

Используется из automation/tg_control_bot.py (команда /blog_health).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _repo_root_from_here() -> Path:
    return Path(__file__).resolve().parent.parent


def format_status_distribution(dist: dict) -> str:
    if not dist:
        return "  (нет данных)"
    items = sorted(dist.items(), key=lambda kv: (-kv[1], kv[0]))
    lines = [f"  - {k}: {v}" for k, v in items[:20]]
    if len(items) > 20:
        lines.append(f"  … ещё {len(items) - 20}")
    return "\n".join(lines)


def format_blog_health_message(data: dict, code: int) -> str:
    if code == 0:
        emoji = "🟢"
    elif code == 2:
        emoji = "🟡"
    elif code == 3:
        emoji = "🔴"
    else:
        emoji = "❌"

    ws = data.get("worksheet_name", "?")
    hdr = data.get("detected_header_row_index", "?")
    total = data.get("total_scanned_rows", "?")
    usable = data.get("usable_rows_after_header", "?")
    norm = data.get("normalized_rows_count", "?")
    pub = data.get("publishable_rows_count", "?")
    empty_n = data.get("empty_status_count", "?")
    share = data.get("empty_status_share")
    if isinstance(share, (int, float)):
        share_s = f"{share:.2%}"
    else:
        share_s = str(share)
    dist = data.get("status_distribution") or {}
    vq = data.get("vitrine_quality") or {}
    sb = vq.get("status_buckets") or {}
    vq_block = ""
    if sb or vq:
        vq_block = (
            "\nVitrine (contract v1):\n"
            f"  DRAFT={sb.get('DRAFT', 0)} APPROVED={sb.get('APPROVED', 0)} "
            f"RTP={sb.get('READY_TO_PUBLISH', 0)} PUBLISHED={sb.get('PUBLISHED', 0)}\n"
            f"  meaningful={vq.get('rows_with_meaningful_content')} "
            f"publishable_v1={vq.get('publishable_v1')} "
            f"content_not_rtp={vq.get('has_content_not_publishable_v1')}\n"
            f"  content_in_DRAFT_or_APPROVED={vq.get('has_content_status_draft_or_approved')}\n"
        )

    return (
        f"{emoji} BLOG HEALTH (exit {code})\n\n"
        f"Worksheet: {ws}\n"
        f"Header row: {hdr}\n\n"
        f"Rows:\n"
        f"  total scanned: {total}\n"
        f"  usable: {usable}\n"
        f"  normalized: {norm}\n\n"
        f"Publish:\n"
        f"  publishable: {pub}\n"
        f"  empty status: {empty_n} ({share_s})\n\n"
        f"Status distribution:\n"
        f"{format_status_distribution(dist)}"
        f"{vq_block}"
    )


def run_blog_health(
    repo_root: str | Path | None = None,
    *,
    min_publishable: int | None = 2,
    max_empty_status_share: float | None = 0.95,
    timeout: int = 180,
) -> tuple[int, str]:
    """
    Запускает smoke-check с --json, парсит stdout.
    Возвращает (returncode, текст для Telegram).
    """
    root = Path(repo_root) if repo_root else _repo_root_from_here()
    script = root / "scripts" / "blog_raw_feed_smoke_check.py"
    if not script.is_file():
        return 1, f"❌ Не найден скрипт: {script}"

    cmd = [
        sys.executable,
        str(script),
        "--json",
    ]
    if min_publishable is not None:
        cmd.extend(["--min-publishable", str(min_publishable)])
    if max_empty_status_share is not None:
        cmd.extend(["--max-empty-status-share", str(max_empty_status_share)])

    proc = subprocess.run(
        cmd,
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=None,  # наследуем окружение бота (GOOGLE_*, SPREADSHEET_ID, …)
    )
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    rc = proc.returncode

    if not out and err:
        return rc, clip_tg(f"❌ Нет JSON в stdout.\nstderr:\n{err}")

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        tail = out[-800:] if len(out) > 800 else out
        extra = f"\n\nstderr:\n{err}" if err else ""
        return 1, clip_tg(f"❌ Ошибка разбора JSON.\nstdout (хвост):\n{tail}{extra}")

    msg = format_blog_health_message(data, rc)
    return rc, clip_tg(msg)


def clip_tg(text: str, limit: int = 3500) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 80] + "\n…(truncated)…\n" + text[-60:]
