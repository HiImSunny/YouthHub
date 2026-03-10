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
    get_default_model,
)
from .hardware import get_hardware_info
from core.permissions import get_manageable_orgs, group_orgs_by_root

AVAILABLE_MODELS = [
    {'id': 'sailor2:1b', 'name': 'Sailor 2 1B (Mặc định - Siêu nhẹ)', 'vram': 1.5},
    {'id': 'sailor2:8b', 'name': 'Sailor 2 8B (Nâng cao - SEO/Văn bản)', 'vram': 6.0},
    {'id': 'sailor2:20b', 'name': 'Sailor 2 20B (Cực mạnh - Yêu cầu GPU khủng)', 'vram': 15.0},
    {'id': 'qwen3:1.7b', 'name': 'Qwen 3 1.7B (Thông minh - Nhanh)', 'vram': 2.5},
    {'id': 'qwen3:4b', 'name': 'Qwen 3 4B (Cân bằng)', 'vram': 4.5},
    {'id': 'qwen3:8b', 'name': 'Qwen 3 8B (Sáng tạo cao)', 'vram': 7.0},
    {'id': 'qwen2.5:1.5b-instruct', 'name': 'Qwen 2.5 1.5B (Cũ - Nhanh)', 'vram': 1.5},
    {'id': 'qwen2.5:3b-instruct', 'name': 'Qwen 2.5 3B (Cũ - GPU)', 'vram': 3.5},
]


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
    
    manageable_orgs = get_manageable_orgs(request.user).order_by('type', 'name')

    context = {
        'ollama_status': None,
        'ollama_model': get_default_model(),
        'available_models': AVAILABLE_MODELS,
        'recent_docs': recent_docs,
        'manageable_orgs': manageable_orgs,
        'org_groups': group_orgs_by_root(manageable_orgs),
        'hardware_info': get_hardware_info(),
        'output': '',
    }
    return render(request, 'ai_assistant/chat.html', context)


@login_required
def ollama_status_api(request):
    """Async endpoint: returns Ollama connection status as JSON."""
    status = check_ollama_status()
    # Thêm default_model hiện tại vào response để update UI
    status['current_default'] = get_default_model()
    return JsonResponse(status)


@login_required
@require_POST
def ai_suggest_api(request):
    """Ajax endpoint for quick AI suggestions"""
    import json
    if request.user.role == 'STUDENT':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    try:
        data = json.loads(request.body)
        prompt_text = data.get('prompt', '')
    except:
        prompt_text = request.POST.get('prompt', '')
        
    if not prompt_text:
         return JsonResponse({'error': 'No prompt provided'}, status=400)
         
    import requests
    from django.conf import settings
    from .ollama_service import generate_document
    
    OLLAMA_BASE_URL = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_TIMEOUT = getattr(settings, 'OLLAMA_TIMEOUT', 120)
    
    try:
        resp = requests.post(f'{OLLAMA_BASE_URL}/api/generate', json={
            'model': get_default_model(),
            'prompt': prompt_text,
            'stream': False
        }, timeout=OLLAMA_TIMEOUT)
        
        if resp.status_code == 200:
            return JsonResponse({'content': resp.json().get('response', '')})
        return JsonResponse({'error': f'Ollama error {resp.status_code}: {resp.text}'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def pull_model_api(request):
    """Ajax endpoint to stream Ollama model pull progress."""
    import json
    import requests
    from django.conf import settings

    if request.user.role == 'STUDENT':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        model_name = data.get('model_name')
    except:
        model_name = request.POST.get('model_name')

    if not model_name:
        return JsonResponse({'error': 'No model_name provided'}, status=400)

    OLLAMA_BASE_URL = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')

    def event_stream():
        try:
            # Stream the POST request to Ollama
            with requests.post(
                f'{OLLAMA_BASE_URL}/api/pull',
                json={'name': model_name, 'stream': True},
                stream=True,
                timeout=3600 # 1 hour timeout for huge models
            ) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if line:
                        yield line.decode('utf-8') + '\n'
        except Exception as e:
            yield json.dumps({'error': str(e)}) + '\n'

    from django.http import StreamingHttpResponse
    response = StreamingHttpResponse(event_stream(), content_type='application/x-ndjson')
    response['X-Accel-Buffering'] = 'no'
    response['Cache-Control'] = 'no-cache'
    return response


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
    description = request.POST.get('description', '')
    model_name = request.POST.get('model_name', get_default_model())

    manageable_orgs = get_manageable_orgs(request.user).order_by('type', 'name')

    import time
    start_time = time.time()
    # Try Ollama first
    result = generate_document(doc_type, event_name, organization, date, description, model_name=model_name)
    generation_time = round(time.time() - start_time, 1)

    if result.get('error'):
        # Pass an offline status directly back so UI shows correct state without relying async
        status = {
            'online': result.get('status_code') != 404,
            'has_model': False,
            'models': []
        }
        # Fallback to template
        content = generate_fallback(doc_type, event_name, organization, date, description)
        messages.warning(request, f'Ollama gặp lỗi. Lỗi: {result["error"][:100]}')
    else:
        status = None # let async handle it if success
        content = result['content']

    # Save as RAW document
    doc = AiDocument.objects.create(
        created_by=request.user,
        doc_type=_map_doc_type(doc_type),
        title=f'{doc_type}: {event_name or "Chưa có tên"}',
        prompt=f'Type: {doc_type} | Event: {event_name} | Org: {organization} | Date: {date}',
        generated_content=content,
        model=result.get('model', model_name),
        tokens_input=result.get('tokens_input'),
        tokens_output=result.get('tokens_output'),
        status=AiDocument.DocStatus.RAW,
    )

    recent_docs = AiDocument.objects.filter(
        created_by=request.user
    ).order_by('-created_at')[:5]

    word_count = len(content.split()) if content else 0

    context = {
        'ollama_status': status,
        'ollama_model': model_name,
        'available_models': AVAILABLE_MODELS,
        'recent_docs': recent_docs,
        'manageable_orgs': manageable_orgs,
        'org_groups': group_orgs_by_root(manageable_orgs),
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
        'form_description': description,
        'hardware_info': get_hardware_info(),
        'generation_time': generation_time,
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
        'BÀI ĐĂNG SOCIAL': 'OTHER',
        'EMAIL THÔNG BÁO': 'INVITATION',
        'KỊCH BẢN MC': 'OTHER',
    }
    return mapping.get(label, 'OTHER')
