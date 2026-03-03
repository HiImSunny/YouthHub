from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def sessions_view(request):
    """Placeholder - will be developed in Phase 3."""
    return render(request, 'attendance/sessions.html')
