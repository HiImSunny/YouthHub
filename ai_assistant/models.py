from django.conf import settings
from django.db import models


class AiDocument(models.Model):
    """
    AI-generated documents and generation history.
    Maps to table: ai_documents
    Status RAW = raw AI log; DRAFT/EDITED/FINAL = saved documents.
    """

    class DocType(models.TextChoices):
        PLAN = 'PLAN', 'Kế hoạch'
        REPORT = 'REPORT', 'Báo cáo'
        INVITATION = 'INVITATION', 'Thư mời'
        OTHER = 'OTHER', 'Khác'

    class DocStatus(models.TextChoices):
        RAW = 'RAW', 'Bản thô AI'
        DRAFT = 'DRAFT', 'Bản nháp'
        EDITED = 'EDITED', 'Đã chỉnh sửa'
        FINAL = 'FINAL', 'Bản chính thức'

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
    generated_content = models.TextField()
    model = models.CharField(max_length=100, default='qwen2.5-coder:1.5b')
    tokens_input = models.IntegerField(blank=True, null=True)
    tokens_output = models.IntegerField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=DocStatus.choices,
        default=DocStatus.RAW,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_documents'
        verbose_name = 'Văn bản AI'
        verbose_name_plural = 'Văn bản AI'
        ordering = ['-created_at']

    def __str__(self):
        return self.title or f"AI Doc #{self.pk}"




