from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import AiDocument
from .ollama_service import (
    check_ollama_status,
    generate_document,
    generate_fallback,
    OLLAMA_MODEL,
)


def _staff_only(request):
    """Return redirect response if user is STUDENT, else None."""
    if request.user.role == 'STUDENT':
        messages.error(request, 'Sinh viên không có quyền truy cập trang này.')
        return redirect('students:dashboard')
    return None


@login_required
def chat_view(request):
    """Main AI assistant page. Renders immediately; Ollama status is fetched async by JS."""
    if (denied := _staff_only(request)):
        return denied
    recent_docs = AiDocument.objects.filter(
        created_by=request.user
    ).order_by('-created_at')[:5]

    context = {
        'ollama_status': None,   # Will be fetched asynchronously by frontend
        'ollama_model': OLLAMA_MODEL,
        'recent_docs': recent_docs,
        'output': '',
    }
    return render(request, 'ai_assistant/chat.html', context)


@login_required
def ollama_status_api(request):
    """Async endpoint: returns Ollama connection status as JSON."""
    status = check_ollama_status()
    return JsonResponse(status)


@login_required
@require_POST
def generate_view(request):
    """Handle document generation request."""
    if (denied := _staff_only(request)):
        return denied
    doc_type = request.POST.get('doc_type', 'KẾ HOẠCH / BÁO CÁO')
    event_name = request.POST.get('event_name', '')
    organization = request.POST.get('organization', '')
    date = request.POST.get('date', '')

    # Try Ollama first
    result = generate_document(doc_type, event_name, organization, date)

    if result.get('error'):
        # Fallback to template
        content = generate_fallback(doc_type, event_name, organization, date)
        messages.warning(request, f'Ollama offline — dùng bản mẫu. Lỗi: {result["error"][:100]}')
    else:
        content = result['content']

    # Save as RAW document
    doc = AiDocument.objects.create(
        created_by=request.user,
        doc_type=_map_doc_type(doc_type),
        title=f'{doc_type}: {event_name or "Chưa có tên"}',
        prompt=f'Type: {doc_type} | Event: {event_name} | Org: {organization} | Date: {date}',
        generated_content=content,
        model=result.get('model', OLLAMA_MODEL),
        tokens_input=result.get('tokens_input'),
        tokens_output=result.get('tokens_output'),
        status=AiDocument.DocStatus.RAW,
    )

    # Re-render chat page with output (status fetched async by JS)
    status = {'online': True, 'models': [], 'has_model': True}  # optimistic after generate
    recent_docs = AiDocument.objects.filter(
        created_by=request.user
    ).order_by('-created_at')[:5]

    word_count = len(content.split()) if content else 0

    context = {
        'ollama_status': status,
        'ollama_model': OLLAMA_MODEL,
        'recent_docs': recent_docs,
        'output': content,
        'current_doc': doc,
        'word_count': word_count,
        'tokens_in': result.get('tokens_input', 0),
        'tokens_out': result.get('tokens_output', 0),
        # Preserve form values
        'form_doc_type': doc_type,
        'form_event_name': event_name,
        'form_organization': organization,
        'form_date': date,
    }
    return render(request, 'ai_assistant/chat.html', context)


@login_required
def documents_list(request):
    """List all saved AI documents for current user."""
    if request.user.role in ('ADMIN', 'STAFF'):
        docs = AiDocument.objects.select_related('created_by').all()
    else:
        docs = AiDocument.objects.filter(created_by=request.user)

    return render(request, 'ai_assistant/documents.html', {'documents': docs})


@login_required
def document_detail(request, pk):
    """View a single document and allow editing."""
    doc = get_object_or_404(AiDocument, pk=pk)

    if request.method == 'POST':
        # Update content
        doc.generated_content = request.POST.get('content', doc.generated_content)
        doc.title = request.POST.get('title', doc.title)
        if doc.status == AiDocument.DocStatus.RAW:
            doc.status = AiDocument.DocStatus.EDITED
        doc.save()
        messages.success(request, 'Đã lưu thay đổi!')
        return redirect('ai_assistant:document_detail', pk=pk)

    word_count = len(doc.generated_content.split()) if doc.generated_content else 0
    return render(request, 'ai_assistant/document_detail.html', {
        'doc': doc,
        'word_count': word_count,
    })


@login_required
@require_POST
def document_save(request, pk):
    """Save document as DRAFT status."""
    doc = get_object_or_404(AiDocument, pk=pk)
    doc.status = AiDocument.DocStatus.DRAFT
    doc.save()
    messages.success(request, f'Đã lưu "{doc.title}" thành bản nháp!')
    return redirect('ai_assistant:documents')


@login_required
@require_POST
def document_delete(request, pk):
    """Delete an AI document."""
    doc = get_object_or_404(AiDocument, pk=pk)
    if doc.created_by != request.user and request.user.role != 'ADMIN':
        messages.error(request, 'Bạn không có quyền xóa văn bản này.')
        return redirect('ai_assistant:documents')

    doc.delete()
    messages.success(request, 'Đã xóa văn bản.')
    return redirect('ai_assistant:documents')


# ────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────
def _map_doc_type(label: str) -> str:
    """Map form label to model DocType."""
    mapping = {
        'KẾ HOẠCH / BÁO CÁO': 'PLAN',
        'BIÊN BẢN HỌP': 'REPORT',
        'TỜ TRÌNH': 'INVITATION',
        'CÔNG VĂN': 'OTHER',
    }
    return mapping.get(label, 'OTHER')
