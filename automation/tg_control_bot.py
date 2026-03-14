#!/usr/bin/env python3
import os
import shlex
import subprocess
from pathlib import Path
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

MAX_TG = 3500  # запас до лимита Telegram


def clip(text: str, limit: int = MAX_TG) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 80] + "\n…(truncated)…\n" + text[-60:]


def get_allowed_ids() -> set[int]:
    raw = os.environ.get("TG_CONTROL_ALLOWED_IDS", "").strip()
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


def runner_cwd() -> str:
    p = (os.environ.get("MW_RUNNER_REPO_PATH") or "").strip()
    if not p:
        p = (os.environ.get("MW_REPO_PATH") or "").strip()
    if not p:
        raise RuntimeError("MW_RUNNER_REPO_PATH/MW_REPO_PATH не задан")
    return p


def run_cmd(cmd: list[str], cwd: str, timeout: int = 120) -> tuple[int, str]:
    p = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        env=os.environ.copy(),
    )
    return p.returncode, (p.stdout or "")


def is_allowed(update: Update) -> bool:
    allowed = get_allowed_ids()
    uid = update.effective_user.id if update.effective_user else None
    return (uid is not None) and (uid in allowed)


async def guard(update: Update) -> bool:
    if not is_allowed(update):
        await update.message.reply_text("⛔️ Доступ запрещён.")
        return False
    return True


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return
    await update.message.reply_text("✅ ok")


async def cmd_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id if update.effective_user else None
    uname = update.effective_user.username if update.effective_user else None
    await update.message.reply_text(f"user_id={uid}\nusername=@{uname}")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 MyWave Control Bot\n\n"
        "Команды:\n"
        "/ping — проверка связи\n"
        "/whoami — твой user_id\n"
        "/status — git status (ветка/изменения)\n"
        "/diff — git diff --stat\n"
        "/doctor — диагностика окружения (scripts/doctor.py)\n"
        "/task <текст> — запустить Cursor Agent CLI с задачей\n\n"
        "Примеры:\n"
        "/task покажи git status\n"
        "/task найди где определяется SECRET_KEY и как лучше хранить .env\n"
        "/task проверь, что на странице Wake Challenge не трогаем остальные страницы\n"
    )
    await update.message.reply_text(text)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return
    cwd = runner_cwd()
    rc, out = run_cmd(["git", "status", "-sb"], cwd=cwd, timeout=60)
    await update.message.reply_text(clip(out))


async def cmd_doctor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return
    cwd = runner_cwd()
    rc, out = run_cmd(["python3", "scripts/doctor.py"], cwd=cwd, timeout=180)
    await update.message.reply_text(clip(out))


async def cmd_diff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return
    cwd = runner_cwd()
    rc, out = run_cmd(["git", "diff", "--stat"], cwd=cwd, timeout=60)
    await update.message.reply_text(clip(out))


async def cmd_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return

    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("Формат: /task <что сделать>")
        return

    cwd = runner_cwd()

    cmd = [
        "agent",
        "--print",
        "--trust",
        "--workspace", cwd,
        text
    ]

    try:
        rc, out = run_cmd(cmd, cwd=cwd, timeout=600)
        await update.message.reply_text(clip(out))
    except Exception as e:
        await update.message.reply_text(f"Ошибка выполнения:\n{e}")


def main():
    token = os.environ.get("TG_CONTROL_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TG_CONTROL_BOT_TOKEN не задан в окружении")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_help))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("whoami", cmd_whoami))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("doctor", cmd_doctor))
    app.add_handler(CommandHandler("diff", cmd_diff))
    app.add_handler(CommandHandler("task", cmd_task))

    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
