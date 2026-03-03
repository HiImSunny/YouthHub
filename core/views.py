from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
import json

from activities.models import Activity
from attendance.models import AttendanceRecord
from .models import Organization, Semester, AuditLog
from .decorators import admin_required, staff_required


@login_required
def dashboard_view(request):
    """Main dashboard with summary statistics."""
    now = timezone.now()
    context = {
        'total_activities': Activity.objects.count(),
        'pending_count': Activity.objects.filter(status='PENDING').count(),
        'ongoing_count': Activity.objects.filter(status__in=['APPROVED', 'ONGOING']).count(),
        'total_organizations': Organization.objects.filter(status=True).count(),
        'current_semester': Semester.objects.filter(is_current=True).first(),
        'recent_activities': Activity.objects.select_related('organization', 'created_by').order_by('-created_at')[:7],
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def organizations_view(request):
    """List all organizations in tree structure."""
    orgs = Organization.objects.filter(status=True).select_related('parent').order_by('type', 'name')
    context = {'organizations': orgs}
    return render(request, 'core/organizations.html', context)


@staff_required
def statistics_view(request):
    """
    Advanced statistics page with Chart.js data.
    Accessible by ADMIN and STAFF.
    """
    # ── Activity stats by status ────────────────────────────────────────────
    status_qs = (
        Activity.objects.values('status')
        .annotate(count=Count('id'))
        .order_by('status')
    )
    status_labels = [s['status'] for s in status_qs]
    status_data = [s['count'] for s in status_qs]

    # ── Activity stats by type ───────────────────────────────────────────────
    type_qs = (
        Activity.objects.values('activity_type')
        .annotate(count=Count('id'))
        .order_by('activity_type')
    )
    type_labels = [t['activity_type'] for t in type_qs]
    type_data = [t['count'] for t in type_qs]

    # ── Monthly activity creation (last 6 months) ────────────────────────────
    six_months_ago = timezone.now() - timezone.timedelta(days=180)
    monthly_qs = (
        Activity.objects
        .filter(created_at__gte=six_months_ago)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    monthly_labels = [m['month'].strftime('%m/%Y') for m in monthly_qs]
    monthly_data = [m['count'] for m in monthly_qs]

    # ── Budget stats ─────────────────────────────────────────────────────────
    from activities.models import Budget
    budget_total = Budget.objects.filter(status='APPROVED').aggregate(total=Sum('total_amount'))['total'] or 0

    # ── Attendance stats ─────────────────────────────────────────────────────
    total_checkins = AttendanceRecord.objects.filter(status='VERIFIED').count()

    # ── Organization breakdown ───────────────────────────────────────────────
    org_qs = (
        Organization.objects
        .filter(status=True)
        .values('type')
        .annotate(count=Count('id'))
    )
    org_labels = [o['type'] for o in org_qs]
    org_data = [o['count'] for o in org_qs]

    context = {
        # Chart.js data (JSON-safe)
        'status_labels': json.dumps(status_labels),
        'status_data': json.dumps(status_data),
        'type_labels': json.dumps(type_labels),
        'type_data': json.dumps(type_data),
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_data': json.dumps(monthly_data),
        'org_labels': json.dumps(org_labels),
        'org_data': json.dumps(org_data),
        # Summary figures
        'total_activities': Activity.objects.count(),
        'total_organizations': Organization.objects.filter(status=True).count(),
        'budget_total': budget_total,
        'total_checkins': total_checkins,
        'pending_count': Activity.objects.filter(status='PENDING').count(),
    }
    return render(request, 'core/statistics.html', context)


@admin_required
def audit_log_view(request):
    """View audit logs. ADMIN only."""
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')

    # Filter by action
    action_filter = request.GET.get('action')
    if action_filter:
        logs = logs.filter(action=action_filter)

    # Filter by object type
    obj_type = request.GET.get('type')
    if obj_type:
        logs = logs.filter(object_type__icontains=obj_type)

    # Search by user
    user_q = request.GET.get('user')
    if user_q:
        logs = logs.filter(user__full_name__icontains=user_q)

    context = {
        'logs': logs[:200],  # Limit to last 200
        'action_choices': AuditLog.Action.choices,
        'current_action': action_filter or '',
        'current_type': obj_type or '',
        'current_user': user_q or '',
    }
    return render(request, 'core/audit_log.html', context)
