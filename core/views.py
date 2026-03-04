from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
import json

from activities.models import Activity
from attendance.models import AttendanceRecord
from .models import Organization, OrganizationMember, Semester, AuditLog
from .decorators import admin_required, staff_required
from .permissions import can_manage_org_staff, can_create_org, get_manageable_orgs


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
    """List all organizations. B4: Only admin sees Create button."""
    orgs = Organization.objects.filter(status=True).select_related('parent').annotate(
        member_count=Count('members')
    ).order_by('type', 'name')
    context = {
        'organizations': orgs,
        'can_create_org': can_create_org(request.user),  # B4
        'manageable_org_ids': set(  # B3: which orgs can user manage staff for
            get_manageable_orgs(request.user).values_list('id', flat=True)
        ),
    }
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


# ─── B4: Create Organization (Admin Only) ─────────────────────────────────────

@admin_required
def organization_create(request):
    """B4: Create a new organization. ADMIN only."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        org_type = request.POST.get('type', '')
        parent_id = request.POST.get('parent') or None
        description = request.POST.get('description', '').strip()

        if not name or not code or not org_type:
            messages.error(request, 'Vui long dien day du thong tin bat buoc.')
        elif Organization.objects.filter(code__iexact=code).exists():
            messages.error(request, 'Ma to chuc da ton tai.')
        else:
            org = Organization.objects.create(
                name=name,
                code=code.upper(),
                type=org_type,
                parent_id=parent_id,
                description=description,
                status=True,
            )
            messages.success(request, f'Da tao to chuc "{org.name}" thanh cong!')
            return redirect('core:organizations')

    context = {
        'parent_orgs': Organization.objects.filter(status=True).order_by('type', 'name'),
        'type_choices': Organization.OrgType.choices,
    }
    return render(request, 'core/organization_form.html', context)


# ─── B3: Manage Staff of Child Orgs ──────────────────────────────────────────

@login_required
def org_staff_view(request, org_pk):
    """
    B3: View and manage staff (OrganizationMember with is_officer=True) of an org.
    - Admin: can manage any org's staff.
    - Parent Staff: can manage staff of their child orgs.
    """
    org = get_object_or_404(Organization, pk=org_pk, status=True)

    if not can_manage_org_staff(request.user, org):
        messages.error(request, 'Ban khong co quyen quan ly nhan su cua to chuc nay.')
        return redirect('core:organizations')

    from django.contrib.auth import get_user_model
    User = get_user_model()

    members = OrganizationMember.objects.filter(
        organization=org
    ).select_related('user').order_by('-is_officer', 'user__full_name')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_officer':
            user_id = request.POST.get('user_id')
            position = request.POST.get('position', 'Can bo').strip()
            try:
                target_user = User.objects.get(pk=user_id, role='STAFF')
                member, created = OrganizationMember.objects.get_or_create(
                    organization=org,
                    user=target_user,
                    defaults={
                        'position': position,
                        'is_officer': True,
                        'joined_at': timezone.now().date(),
                    }
                )
                if not created:
                    member.is_officer = True
                    member.position = position
                    member.save(update_fields=['is_officer', 'position'])
                messages.success(request, f'Da them "{target_user.full_name}" lam can bo.')
            except User.DoesNotExist:
                messages.error(request, 'Khong tim thay user hoac user khong phai Staff.')

        elif action == 'remove_officer':
            member_id = request.POST.get('member_id')
            member = OrganizationMember.objects.filter(pk=member_id, organization=org).first()
            if member:
                member.is_officer = False
                member.save(update_fields=['is_officer'])
                messages.success(request, f'Da xoa quyen can bo khoi "{member.user.full_name}".')

        elif action == 'remove_member':
            member_id = request.POST.get('member_id')
            member = OrganizationMember.objects.filter(pk=member_id, organization=org).first()
            if member:
                member.delete()
                messages.success(request, 'Da xoa thanh vien khoi to chuc.')

        return redirect('core:org_staff', org_pk=org_pk)

    # Available staff users not yet in this org
    existing_user_ids = members.values_list('user_id', flat=True)
    available_staff = User.objects.filter(role='STAFF', status='ACTIVE').exclude(
        pk__in=existing_user_ids
    ).order_by('full_name')

    context = {
        'org': org,
        'members': members,
        'available_staff': available_staff,
    }
    return render(request, 'core/org_staff.html', context)
