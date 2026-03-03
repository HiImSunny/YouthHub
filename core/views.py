from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from activities.models import Activity
from .models import Organization, Semester


@login_required
def dashboard_view(request):
    """Main dashboard with summary statistics."""
    context = {
        'total_activities': Activity.objects.count(),
        'pending_activities': Activity.objects.filter(status='PENDING').count(),
        'active_activities': Activity.objects.filter(status__in=['APPROVED', 'ONGOING']).count(),
        'total_orgs': Organization.objects.filter(status=True).count(),
        'current_semester': Semester.objects.filter(is_current=True).first(),
        'recent_activities': Activity.objects.order_by('-created_at')[:5],
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def organizations_view(request):
    """List all organizations in tree structure."""
    orgs = Organization.objects.filter(status=True).select_related('parent').order_by('type', 'name')
    context = {'organizations': orgs}
    return render(request, 'core/organizations.html', context)
