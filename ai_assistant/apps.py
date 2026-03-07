from django.apps import AppConfig
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class AiAssistantConfig(AppConfig):
    name = 'ai_assistant'
    
    def ready(self):
        from .hardware import detect_best_model
        
        # We only override if it's not already overridden in settings heavily or we just force it
        # Actually, let's just force the hardware selection to be stored in settings 
        # so everything picks it up easily.
        best_model = detect_best_model()
        
        # Override the setting so ollama_service.py can just read it or we set it in ollama
        settings.OLLAMA_MODEL = best_model
        
        logger.info(f"AiAssistantConfig: Auto-configured model to {best_model} based on hardware.")
