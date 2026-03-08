from django.contrib import admin
from .models import AiDocument


@admin.register(AiDocument)
class AiDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'doc_type', 'created_by', 'status', 'created_at')
    list_filter = ('doc_type', 'status')
    search_fields = ('title', 'prompt')
