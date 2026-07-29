#!/usr/bin/env bash
# Tour only: msk-1-vm-9j6k — Telegram program callback live smoke
# Source: Owner session 2026-07-29
set -Eeuo pipefail
set +H
umask 077

EXPECTED_HOST="msk-1-vm-9j6k"
API_CONTAINER="toutism-api-1"
DB_CONTAINER="toutism-postgres-1"
EXPECTED_API_IMAGE="sha256:05b6f1a1b514a656261241e5c54881afa44e8e72bbc8075c163b2adfe570f79f"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
AUDIT_DIR="/opt/mywave/backups/telegram-program-callback-live-smoke-${STAMP}"

test "$(hostname)" = "$EXPECTED_HOST"
test "$(docker inspect -f '{{.State.Status}}' "$API_CONTAINER")" = "running"
test "$(docker inspect -f '{{.State.Health.Status}}' "$API_CONTAINER")" = "healthy"
test "$(docker inspect -f '{{.Image}}' "$API_CONTAINER")" = "$EXPECTED_API_IMAGE"
test "$(docker inspect -f '{{.State.Health.Status}}' "$DB_CONTAINER")" = "healthy"

install -d -m 700 "$AUDIT_DIR"

DB_USER="$(
  docker exec "$API_CONTAINER" \
    node -p 'new URL(process.env.DATABASE_URL).username'
)"

DB_NAME="$(
  docker exec "$API_CONTAINER" \
    node -p 'new URL(process.env.DATABASE_URL).pathname.slice(1)'
)"

echo "===== TELEGRAM PROGRAM CALLBACK LIVE SMOKE ====="

echo
echo "===== PROGRAM DATABASE FINGERPRINT BEFORE ====="

docker exec -i "$DB_CONTAINER" \
  psql -v ON_ERROR_STOP=1 -At -U "$DB_USER" -d "$DB_NAME" \
  > "$AUDIT_DIR/programs-before.txt" <<'SQL'
BEGIN;

SELECT
  count(*) || '|' ||
  md5(
    coalesce(
      string_agg(
        "id" || ':' || "publishStatus" || ':' || "updatedAt"::text,
        '|' ORDER BY "id"
      ),
      ''
    )
  )
FROM programs;

ROLLBACK;
SQL

cat "$AUDIT_DIR/programs-before.txt"

CLICK_SINCE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo
echo "===== SEND ONE REAL PROGRAM MENU ====="

docker exec -i "$API_CONTAINER" node \
  > "$AUDIT_DIR/send-program-menu-result.safe.json" <<'NODE'
const { prisma } = require(
  "/app/services/api/dist/lib/prisma.js",
);

const { callTelegramJson } = require(
  "/app/services/api/dist/modules/telegram/telegramApi.js",
);

function truncate(value, limit = 44) {
  const characters = Array.from(value);

  return characters.length <= limit
    ? value
    : `${characters.slice(0, limit - 1).join("")}…`;
}

function buttonLabel(value, limit = 44) {
  const normalized = value
    .replace(/[\u0000-\u001f\u007f-\u009f]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  return truncate(normalized || "Без названия", limit);
}

const statusLabels = {
  draft: "Черновик",
  internal_review: "Проверка",
  needs_fix: "Доработать",
  approved: "Одобрена",
  paused: "На паузе",
  archived: "В архиве",
};

function safeError(error) {
  return {
    name: error?.name ?? null,
    message: String(error?.message ?? error)
      .replace(
        /postgres(?:ql)?:\/\/[^\s"']+/gi,
        "postgresql://[redacted]",
      )
      .replace(
        /bot[0-9]+:[A-Za-z0-9_-]+/g,
        "bot[redacted]",
      ),
  };
}

(async () => {
  const report = {
    sent: false,
    programCount: 0,
    messageId: null,
    telegramDescription: null,
    webhook: null,
  };

  const chatId =
    process.env.TELEGRAM_CONTENT_OWNER_CHAT_ID?.trim() ||
    process.env.TELEGRAM_ALERT_CHAT_ID?.trim();

  if (!chatId) {
    report.telegramDescription =
      "Telegram owner chat is not configured";

    console.log(JSON.stringify(report, null, 2));
    return;
  }

  const programs = await prisma.program.findMany({
    where: {
      publishStatus: {
        not: "published",
      },
    },
    select: {
      id: true,
      title: true,
      publishStatus: true,
    },
    orderBy: {
      updatedAt: "desc",
    },
    take: 8,
  });

  report.programCount = programs.length;

  const keyboard = {
    inline_keyboard: [
      ...programs.map((program) => [{
        text:
          `${buttonLabel(program.title)} · ` +
          `${statusLabels[program.publishStatus] ?? program.publishStatus}`,
        callback_data: `mw:program:${program.id}`,
      }]),
      [{
        text: "← Меню",
        callback_data: "mw:menu",
      }],
    ],
  };

  try {
    const response = await callTelegramJson(
      process.env,
      "sendMessage",
      {
        chat_id: chatId,
        text:
          "Диагностика меню программ. " +
          "Нажмите только первую программу. " +
          "Статус на этом шаге не изменяется.",
        reply_markup: keyboard,
      },
    );

    report.sent = response.ok === true;
    report.telegramDescription =
      response.ok
        ? null
        : response.description ?? "unknown Telegram error";

    report.messageId =
      response.result &&
      typeof response.result === "object" &&
      Number.isInteger(response.result.message_id)
        ? response.result.message_id
        : null;
  } catch (error) {
    report.sendException = safeError(error);
  }

  try {
    const webhook = await callTelegramJson(
      process.env,
      "getWebhookInfo",
      {},
    );

    let webhookHost = null;

    if (
      webhook.ok &&
      webhook.result &&
      typeof webhook.result === "object" &&
      typeof webhook.result.url === "string" &&
      webhook.result.url
    ) {
      try {
        webhookHost = new URL(webhook.result.url).host;
      } catch {
        webhookHost = "invalid-url";
      }
    }

    report.webhook = {
      ok: webhook.ok === true,
      host: webhookHost,
      pendingUpdates:
        webhook.result &&
        typeof webhook.result === "object"
          ? webhook.result.pending_update_count ?? null
          : null,
      lastError:
        webhook.result &&
        typeof webhook.result === "object"
          ? webhook.result.last_error_message ?? null
          : null,
    };
  } catch (error) {
    report.webhook = {
      ok: false,
      error: safeError(error),
    };
  }

  console.log(JSON.stringify(report, null, 2));
})()
  .catch((error) => {
    console.log(JSON.stringify({
      sent: false,
      fatalError: safeError(error),
    }, null, 2));
  })
  .finally(async () => {
    await prisma.$disconnect().catch(() => undefined);
  });
NODE

cat "$AUDIT_DIR/send-program-menu-result.safe.json"

if grep -q '"sent": true' \
  "$AUDIT_DIR/send-program-menu-result.safe.json"; then

  echo
  echo "Сообщение отправлено."
  echo "1. Откройте операторский Telegram-чат."
  echo "2. Найдите новое сообщение «Диагностика меню программ»."
  echo "3. Нажмите ТОЛЬКО первую кнопку с названием программы."
  echo "4. Не нажимайте кнопку нового статуса."
  echo "5. Вернитесь в терминал."

  read -r -p \
    "После нажатия первой программы нажмите Enter здесь: " \
    CONFIRM_CLICK

  sleep 3
else
  echo
  echo "PROGRAM_MENU_SEND=FAILED"
  echo "Нажимать кнопку не нужно: Telegram не принял сообщение."
fi

echo
echo "===== CALLBACK LOGS FROM EXACT TEST WINDOW ====="

docker logs \
  --since "$CLICK_SINCE" \
  --timestamps \
  "$API_CONTAINER" 2>&1 |
  sed -E \
    -e 's#bot[0-9]+:[A-Za-z0-9_-]+#bot[redacted]#g' \
    -e 's#postgres(ql)?://[^[:space:]]+#postgresql://[redacted]#g' \
  > "$AUDIT_DIR/callback-window.safe.log"

grep -Ei -C 30 \
  'telegram-webhook|Telegram sendMessage failed|callback|mw:program|bad request|forbidden|error|exception|unhandled' \
  "$AUDIT_DIR/callback-window.safe.log" \
  > "$AUDIT_DIR/callback-relevant.safe.log" || true

if test -s "$AUDIT_DIR/callback-relevant.safe.log"; then
  cat "$AUDIT_DIR/callback-relevant.safe.log"
else
  echo "relevant_callback_errors=NONE_FOUND"
fi

echo
echo "===== PROGRAM DATABASE FINGERPRINT AFTER ====="

docker exec -i "$DB_CONTAINER" \
  psql -v ON_ERROR_STOP=1 -At -U "$DB_USER" -d "$DB_NAME" \
  > "$AUDIT_DIR/programs-after.txt" <<'SQL'
BEGIN;

SELECT
  count(*) || '|' ||
  md5(
    coalesce(
      string_agg(
        "id" || ':' || "publishStatus" || ':' || "updatedAt"::text,
        '|' ORDER BY "id"
      ),
      ''
    )
  )
FROM programs;

ROLLBACK;
SQL

cat "$AUDIT_DIR/programs-after.txt"

cmp \
  "$AUDIT_DIR/programs-before.txt" \
  "$AUDIT_DIR/programs-after.txt"

echo "program_database_unchanged=PASS"

echo
echo "===== API UNCHANGED ====="

docker inspect \
  -f 'id={{.Id}} image={{.Image}} status={{.State.Status}} health={{.State.Health.Status}} restarts={{.RestartCount}}' \
  "$API_CONTAINER" |
  tee "$AUDIT_DIR/api-runtime.txt"

test "$(docker inspect -f '{{.Image}}' "$API_CONTAINER")" = \
  "$EXPECTED_API_IMAGE"

test "$(docker inspect -f '{{.State.Health.Status}}' "$API_CONTAINER")" = \
  "healthy"

echo
echo "===== EVIDENCE CHECKSUMS ====="

(
  cd "$AUDIT_DIR"

  find . \
    -maxdepth 1 \
    -type f \
    ! -name 'SHA256SUMS' \
    -printf '%f\0' |
    sort -z |
    xargs -0 sha256sum \
    > SHA256SUMS

  sha256sum --check SHA256SUMS
)

echo
echo "===== FINAL RESULT ====="
echo "TELEGRAM_PROGRAM_CALLBACK_LIVE_SMOKE=COMPLETE"
echo "PROGRAM_STATUS_CHANGE=NOT_EXECUTED"
echo "PROGRAM_DATABASE_UNCHANGED=PASS"
echo "CONTAINER_CHANGE=NOT_EXECUTED"
echo "AUTOPUBLISH_EXECUTION=HOLD"
echo "AUDIT_DIR=$AUDIT_DIR"
