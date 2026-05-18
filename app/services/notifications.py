import logging
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps

import requests
from flask import current_app, has_app_context

from app.modules.logger import get_logger
from config import Config

logger = get_logger(__name__)


def retry(attempts=3, delay=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(1, attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    logger.info("Уведомление отправлено (попытка %s)", i)
                    return result
                except Exception as e:
                    logger.warning("Попытка %s не удалась: %s", i, e, exc_info=True)
                    time.sleep(delay)
            logger.error("Все попытки отправки уведомления неуспешны")
            return False
        return wrapper
    return decorator


def _cfg(key: str, default=None):
    if has_app_context():
        val = current_app.config.get(key)
        if val not in (None, ""):
            return val
    return os.getenv(key) or getattr(Config, key, None) or default


def _telegram_bot_token() -> str:
    return (
        _cfg("NOTIFICATION_BOT_TOKEN")
        or _cfg("TELEGRAM_BOT_TOKEN")
        or ""
    )


def _telegram_chat_id() -> str:
    return str(
        _cfg("ADMIN_CHAT_ID")
        or _cfg("TELEGRAM_CHAT_ID")
        or _cfg("TRAINER_CHAT_ID")
        or ""
    )


@retry(attempts=3, delay=2)
def send_telegram_notification(name, phone, slot_or_message):
    """
    Отправляет уведомление в Telegram (ADMIN_CHAT_ID или TELEGRAM_CHAT_ID).
    """
    if "\n" in str(slot_or_message):
        message = str(slot_or_message)
    else:
        message = (
            f"📌 Новая запись на тренировку!\n\n"
            f"👤 Имя: {name}\n"
            f"📱 Телефон: {phone}\n"
            f"🕒 Время: {slot_or_message}"
        )

    token = _telegram_bot_token()
    chat_id = _telegram_chat_id()
    if not token or not chat_id:
        logger.warning(
            "telegram_notify_skipped reason=missing_credentials has_token=%s has_chat=%s",
            bool(token),
            bool(chat_id),
        )
        return False

    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": message,
        },
        timeout=15,
    )

    if not response.ok:
        logger.error("Ошибка отправки в Telegram: %s", response.text)
        return False

    return True


def send_admin_email(subject: str, body: str, to_email: str | None = None) -> bool:
    """
    Email администратору (SMTP из .env). Если SMTP не настроен — логируем и возвращаем False.
    """
    to_addr = (to_email or _cfg("WSC_ADMIN_EMAIL") or "y.valeev@gmail.com").strip()
    mail_server = _cfg("MAIL_SERVER", "")
    if not mail_server:
        logger.warning(
            "email_notify_skipped reason=no_mail_server to=%s subject=%s",
            to_addr,
            subject[:80],
        )
        return False

    mail_port = int(_cfg("MAIL_PORT", 587) or 587)
    use_tls = _cfg("MAIL_USE_TLS", True)
    username = _cfg("MAIL_USERNAME", "")
    password = _cfg("MAIL_PASSWORD", "")
    sender = _cfg("MAIL_DEFAULT_SENDER", "noreply@mywavewake.ru")

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(mail_server, mail_port, timeout=20) as smtp:
            if use_tls:
                smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.sendmail(sender, [to_addr], msg.as_string())
        logger.info("email_sent to=%s subject=%s", to_addr, subject[:80])
        return True
    except Exception as e:
        logger.error("email_send_failed to=%s error=%s", to_addr, e, exc_info=True)
        return False


def notify_safari_application(kind: str, form_data: dict) -> None:
    """Telegram + email о заявке WakeSurf Safari."""
    labels = {
        "participant": "участника Safari",
        "partner": "партнёра Safari",
        "media": "медиа Safari",
        "feedback": "отзыва Safari",
    }
    title = labels.get(kind, f"заявки Safari ({kind})")
    lines = [f"🌊 Новая заявка: {title}", ""]
    for key, val in form_data.items():
        if val in (None, "") or key.startswith("_"):
            continue
        lines.append(f"• {key}: {val}")
    text = "\n".join(lines)
    name = form_data.get("full_name") or form_data.get("contact_name") or form_data.get("company_name") or "Safari"
    phone = form_data.get("phone", "")
    try:
        send_telegram_notification(name, phone, text)
    except Exception as e:
        logger.warning("safari_telegram_failed: %s", e)
    try:
        send_admin_email(subject=f"WakeSurf Safari — {title}", body=text)
    except Exception as e:
        logger.warning("safari_email_failed: %s", e)


def notify_wsc_registration(kind: str, form_data: dict) -> None:
    """Telegram + email о новой заявке WakeSurf Challenge."""
    kind_label = "участника" if kind == "participant" else "тренера"
    lines = [
        f"📌 Новая заявка ({kind_label}) — WakeSurf Challenge 2025",
        "",
        f"👤 ФИО: {form_data.get('full_name', '')}",
        f"📱 Телефон: {form_data.get('phone', '')}",
        f"📧 Email: {form_data.get('email', '')}",
    ]
    if kind == "participant":
        lines.extend([
            f"🎂 Год рождения: {form_data.get('birth_year', '')}",
            f"🎯 Уровень: {form_data.get('level', '')}",
            f"📍 Город: {form_data.get('city', '')}",
        ])
        if form_data.get("goals"):
            lines.append(f"📝 Цели: {form_data.get('goals')}")
    else:
        lines.extend([
            f"🏆 Опыт (лет): {form_data.get('experience_years', '')}",
            f"🏢 Клуб: {form_data.get('club') or '—'}",
        ])
        if form_data.get("portfolio_url"):
            lines.append(f"🔗 Портфолио: {form_data.get('portfolio_url')}")

    text = "\n".join(lines)
    try:
        send_telegram_notification(
            form_data.get("full_name", ""),
            form_data.get("phone", ""),
            text,
        )
    except Exception as e:
        logger.warning("wsc_telegram_failed: %s", e)

    try:
        send_admin_email(
            subject=f"WakeSurf Challenge — заявка {kind_label}",
            body=text,
        )
    except Exception as e:
        logger.warning("wsc_email_failed: %s", e)
