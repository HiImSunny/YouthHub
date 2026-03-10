from django.conf import settings
from django.db import models


class AiDocument(models.Model):
    """
    AI-generated documents and generation history.
    Maps to table: ai_documents
    Status RAW = raw AI log; DRAFT/EDITED/FINAL = saved documents.
    """

    class DocType(models.TextChoices):
        PLAN = 'PLAN', 'Ke hoach'
        REPORT = 'REPORT', 'Bao cao'
        INVITATION = 'INVITATION', 'Thu moi'
        OTHER = 'OTHER', 'Khac'

    class DocStatus(models.TextChoices):
        RAW = 'RAW', 'Ban tho AI'
        DRAFT = 'DRAFT', 'Ban nhap'
        EDITED = 'EDITED', 'Da chinh sua'
        FINAL = 'FINAL', 'Ban chinh thuc'

    class GenerationStatus(models.TextChoices):
        """Tracks async Celery task progress for AI generation."""
        PENDING = 'PENDING', 'Dang tao...'
        DONE = 'DONE', 'Hoan thanh'
        ERROR = 'ERROR', 'Loi'

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_documents',
    )
    activity = models.ForeignKey(
        'activities.Activity',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_documents',
    )
    doc_type = models.CharField(
        max_length=20,
        choices=DocType.choices,
        blank=True,
        null=True,
    )
    title = models.CharField(max_length=255, blank=True, null=True)
    prompt = models.TextField()
    generated_content = models.TextField(blank=True, default='')
    model = models.CharField(max_length=100, default='qwen2.5-coder:1.5b')
    tokens_input = models.IntegerField(blank=True, null=True)
    tokens_output = models.IntegerField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=DocStatus.choices,
        default=DocStatus.RAW,
    )

    # --- Async generation tracking ---
    generation_status = models.CharField(
        max_length=10,
        choices=GenerationStatus.choices,
        default=GenerationStatus.DONE,  # DONE as default for backward compatibility
        db_index=True,
    )
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Celery task ID for async generation tracking',
    )
    generation_error = models.TextField(
        blank=True,
        null=True,
        help_text='Error message if generation failed',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_documents'
        verbose_name = 'Van ban AI'
        verbose_name_plural = 'Van ban AI'
        ordering = ['-created_at']

    def __str__(self):
        return self.title or f"AI Doc #{self.pk}"

    @property
    def is_pending(self):
        return self.generation_status == self.GenerationStatus.PENDING

    @property
    def is_done(self):
        return self.generation_status == self.GenerationStatus.DONE
