from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class TelegramBotService:
    """
    Placeholder para integración con python-telegram-bot v20+.

    En Fase 2 se implementará:
    - Application.build() con webhook
    - Handlers para comandos (/start, /medidor <codigo>, /lectura)
    - Mapeo telegram_user_id ↔ lector_id (User.telegram_id)
    - Procesamiento de fotos y geolocalización
    """

    def __init__(self) -> None:
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.webhook_url = settings.TELEGRAM_WEBHOOK_URL
        self.webhook_secret = settings.TELEGRAM_WEBHOOK_SECRET
        self._initialized = False

    async def initialize(self) -> None:
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not set — skipping initialization")
            return
        # TODO: Application.builder().token(self.token).build()
        # TODO: await bot.set_webhook(url=self.webhook_url, secret_token=self.webhook_secret)
        self._initialized = True
        logger.info("Telegram bot placeholder initialized")

    async def shutdown(self) -> None:
        if self._initialized:
            # TODO: await bot.shutdown()
            self._initialized = False
            logger.info("Telegram bot placeholder shut down")


telegram_service = TelegramBotService()
