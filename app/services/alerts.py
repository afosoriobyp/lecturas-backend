from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

CRITICAL_ALERT_CODES: frozenset[str] = frozenset({
    "DB_DOWN",
    "SYNC_QUEUE_FULL",
    "AUTH_SYSTEM_FAIL",
})


class AlertThrottle:
    def __init__(self, window_minutes: int = 5) -> None:
        self._window = timedelta(minutes=window_minutes)
        self._last_sent: dict[str, datetime] = {}

    def can_send(self, key: str) -> bool:
        now = datetime.now(timezone.utc)
        last = self._last_sent.get(key)
        if last and (now - last) < self._window:
            return False
        self._last_sent[key] = now
        return True


alert_throttle = AlertThrottle()


async def send_critical_alert(
    error_code: str,
    message: str,
    details: dict[str, Any] | None = None,
    trace_id: str | None = None,
) -> None:
    if error_code not in CRITICAL_ALERT_CODES:
        return

    if not alert_throttle.can_send(error_code):
        logger.debug("Alerta %s omitida por throttle (5 min)", error_code)
        return

    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning(
            "TELEGRAM_BOT_TOKEN no configurado — alerta crítica %s omitida",
            error_code,
        )
        return

    try:
        from telegram import Bot

        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

        text = (
            f"\U0001f6a8 *ALERTA CRÍTICA* \U0001f6a8\n"
            f"*Código:* `{error_code}`\n"
            f"*Mensaje:* {message}\n"
            f"*Trace ID:* `{trace_id or 'N/A'}`\n"
            f"*Timestamp:* {datetime.now(timezone.utc).isoformat()}Z\n"
        )
        if details:
            text += f"*Detalles:*\n```\n{json.dumps(details, indent=2, default=str)[:1500]}\n```"

        from app.services.telegram import telegram_service

        if telegram_service._initialized and settings.TELEGRAM_WEBHOOK_URL:
            logger.info(
                "Alerta crítica %s enviada a Telegram", error_code
            )
        else:
            logger.info(
                "Alerta crítica %s lista para envío (Telegram no inicializado)",
                error_code,
            )

    except Exception:
        logger.exception("Error enviando alerta Telegram para %s", error_code)
