from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def chat_view(request):
    """Placeholder - will be developed in Phase 4."""
    return render(request, 'ai_assistant/chat.html')
