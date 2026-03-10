from django.apps import AppConfig
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class AiAssistantConfig(AppConfig):
    name = 'ai_assistant'
    
    def ready(self):
        # Disable automatic hardware override because it forces models that might not exist
        # Instead, rely on settings.OLLAMA_MODEL from .env
        pass
