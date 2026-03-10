"""
Celery tasks for AI Assistant.
Handles async document generation via Ollama to avoid blocking HTTP requests.
"""
import logging

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='ai_assistant.generate_document',
    max_retries=0,       # Ollama generation is deterministic, no retry needed
    time_limit=300,      # Hard limit: 5 min
    soft_time_limit=240, # Soft limit: 4 min (raises SoftTimeLimitExceeded)
)
def generate_document_task(
    self,
    document_id: int,
    doc_type: str,
    event_name: str,
    organization: str,
    date: str,
    description: str = '',
    model_name: str = None,
):
    """
    Async Celery task: generate a document via Ollama and save result to AiDocument.

    Args:
        document_id: PK of the AiDocument record (already created with PENDING status)
        doc_type: Template type string (e.g. 'KE HOACH / BAO CAO')
        event_name: Name of the event/activity
        organization: Organization name
        date: Event date string
        description: Optional description
        model_name: Ollama model to use (defaults to settings OLLAMA_MODEL)
    """
    from .models import AiDocument
    from .ollama_service import generate_document, get_default_model, generate_fallback

    target_model = model_name or get_default_model()
    doc = None

    try:
        doc = AiDocument.objects.get(pk=document_id)
    except AiDocument.DoesNotExist:
        logger.error(f"[Celery] AiDocument #{document_id} not found. Task aborted.")
        return {'status': 'error', 'error': 'Document not found'}

    logger.info(f"[Celery] Starting AI generation for document #{document_id} | model={target_model}")

    try:
        result = generate_document(
            doc_type=doc_type,
            event_name=event_name,
            organization=organization,
            date=date,
            description=description,
            model_name=target_model,
        )

        if result.get('error'):
            # Ollama returned an error — use fallback template
            logger.warning(f"[Celery] Ollama error for doc #{document_id}: {result['error']}")
            fallback_content = generate_fallback(doc_type, event_name, organization, date, description)

            doc.generated_content = fallback_content
            doc.generation_status = AiDocument.GenerationStatus.ERROR
            doc.generation_error = result['error']
            doc.model = target_model
            doc.save(update_fields=[
                'generated_content', 'generation_status',
                'generation_error', 'model', 'updated_at',
            ])
            return {'status': 'error', 'document_id': document_id, 'error': result['error']}

        # Success: save content
        doc.generated_content = result['content']
        doc.generation_status = AiDocument.GenerationStatus.DONE
        doc.generation_error = None
        doc.model = result.get('model', target_model)
        doc.tokens_input = result.get('tokens_input')
        doc.tokens_output = result.get('tokens_output')
        doc.status = AiDocument.DocStatus.RAW
        doc.save(update_fields=[
            'generated_content', 'generation_status', 'generation_error',
            'model', 'tokens_input', 'tokens_output', 'status', 'updated_at',
        ])

        logger.info(
            f"[Celery] ✓ Document #{document_id} generated | "
            f"tokens_in={result.get('tokens_input', 0)} "
            f"tokens_out={result.get('tokens_output', 0)}"
        )
        return {
            'status': 'done',
            'document_id': document_id,
            'tokens_input': result.get('tokens_input', 0),
            'tokens_output': result.get('tokens_output', 0),
        }

    except SoftTimeLimitExceeded:
        logger.error(f"[Celery] Task soft time limit exceeded for doc #{document_id}")
        if doc:
            doc.generation_status = AiDocument.GenerationStatus.ERROR
            doc.generation_error = 'Timeout: AI generation exceeded 4 minutes.'
            doc.save(update_fields=['generation_status', 'generation_error', 'updated_at'])
        return {'status': 'error', 'error': 'timeout'}

    except Exception as exc:
        logger.exception(f"[Celery] Unexpected error for doc #{document_id}: {exc}")
        if doc:
            doc.generation_status = AiDocument.GenerationStatus.ERROR
            doc.generation_error = str(exc)[:500]
            doc.save(update_fields=['generation_status', 'generation_error', 'updated_at'])
        return {'status': 'error', 'error': str(exc)}
