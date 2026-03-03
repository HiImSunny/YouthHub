from django.contrib import admin
from .models import AiDocument, AuditLog


@admin.register(AiDocument)
class AiDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'doc_type', 'created_by', 'status', 'created_at')
    list_filter = ('doc_type', 'status')
    search_fields = ('title', 'prompt')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'object_type', 'object_id', 'user', 'ip_address', 'created_at')
    list_filter = ('action', 'object_type')
    search_fields = ('action',)
    readonly_fields = ('user', 'action', 'object_type', 'object_id', 'ip_address', 'created_at')
