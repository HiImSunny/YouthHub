from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import Activity, ActivityRegistration, PointCategory
from core.models import Organization, Semester
from core.permissions import (
    can_create_activity, can_edit_activity, can_approve_activity,
    get_officer_orgs, get_approvable_orgs,
)


@login_required
def activity_list(request):
    """List activities with filtering."""
    qs = Activity.objects.select_related('organization', 'created_by', 'semester')

    # Filter by status
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)

    # Filter by type
    activity_type = request.GET.get('type')
    if activity_type:
        qs = qs.filter(activity_type=activity_type)

    # Search
    search = request.GET.get('q')
    if search:
        qs = qs.filter(title__icontains=search)

    context = {
        'activities': qs.order_by('-created_at'),
        'status_choices': Activity.ActivityStatus.choices,
        'type_choices': Activity.ActivityType.choices,
        'current_status': status or '',
        'current_type': activity_type or '',
        'search_query': search or '',
    }
    return render(request, 'activities/list.html', context)


@login_required
def activity_detail(request, pk):
    """View activity details."""
    activity = get_object_or_404(
        Activity.objects.select_related('organization', 'created_by', 'approved_by', 'semester'),
        pk=pk,
    )
    registrations = activity.registrations.select_related('student').order_by('-registered_at')

    # Check if current user is registered
    user_registration = None
    if request.user.role == 'STUDENT':
        user_registration = activity.registrations.filter(student=request.user).first()

    context = {
        'activity': activity,
        'registrations': registrations,
        'user_registration': user_registration,
        'registration_count': registrations.filter(status='REGISTERED').count(),
        # B1/B2 permission flags - used in template to show/hide buttons
        'can_edit': can_edit_activity(request.user, activity),
        'can_approve': can_approve_activity(request.user, activity),
    }
    return render(request, 'activities/detail.html', context)


@login_required
def activity_create(request):
    """Create a new activity (STAFF/ADMIN only).
    B1: Staff can only select orgs they are officer of.
    """
    if request.user.role == 'STUDENT':
        messages.error(request, 'Ban khong co quyen tao hoat dong.')
        return redirect('activities:list')

    # B1: Get only the orgs this user can create activities for
    allowed_orgs = get_officer_orgs(request.user)

    if request.method == 'POST':
        org_id = request.POST.get('organization')
        org = Organization.objects.filter(pk=org_id, status=True).first()

        # B1: Verify the submitted org is actually allowed
        if not org or not can_create_activity(request.user, org):
            messages.error(request, 'Ban khong co quyen tao hoat dong cho to chuc nay.')
            return render(request, 'activities/form.html', {
                'organizations': allowed_orgs,
                'semesters': Semester.objects.all().order_by('-start_date'),
                'point_categories': PointCategory.objects.filter(is_active=True).order_by('code'),
                'type_choices': Activity.ActivityType.choices,
            })

        activity = Activity(
            title=request.POST.get('title'),
            code=request.POST.get('code'),
            description=request.POST.get('description'),
            activity_type=request.POST.get('activity_type'),
            start_time=request.POST.get('start_time'),
            end_time=request.POST.get('end_time'),
            location=request.POST.get('location'),
            organization=org,
            semester_id=request.POST.get('semester') or None,
            point_category_id=request.POST.get('point_category') or None,
            created_by=request.user,
            status=Activity.ActivityStatus.DRAFT,
        )
        activity.save()
        messages.success(request, f'Da tao hoat dong "{activity.title}" thanh cong!')
        return redirect('activities:detail', pk=activity.pk)

    context = {
        'organizations': allowed_orgs,  # B1: filtered list
        'semesters': Semester.objects.all().order_by('-start_date'),
        'point_categories': PointCategory.objects.filter(is_active=True).order_by('code'),
        'type_choices': Activity.ActivityType.choices,
    }
    return render(request, 'activities/form.html', context)


@login_required
def activity_edit(request, pk):
    """Edit activity (only DRAFT status, with B1 permission check)."""
    activity = get_object_or_404(Activity, pk=pk)

    if activity.status != 'DRAFT':
        messages.error(request, 'Chi co the chinh sua hoat dong o trang thai Nhap.')
        return redirect('activities:detail', pk=pk)

    # B1: Check edit permission
    if not can_edit_activity(request.user, activity):
        messages.error(request, 'Ban khong co quyen chinh sua hoat dong nay.')
        return redirect('activities:detail', pk=pk)

    # B1: Staff only sees their own orgs, Admin sees all
    allowed_orgs = get_officer_orgs(request.user)

    if request.method == 'POST':
        org_id = request.POST.get('organization')
        org = Organization.objects.filter(pk=org_id, status=True).first()

        # B1: Verify the submitted org is actually allowed
        if not org or not can_create_activity(request.user, org):
            messages.error(request, 'Ban khong co quyen gan hoat dong cho to chuc nay.')
            return render(request, 'activities/form.html', {
                'activity': activity,
                'organizations': allowed_orgs,
                'semesters': Semester.objects.all().order_by('-start_date'),
                'point_categories': PointCategory.objects.filter(is_active=True).order_by('code'),
                'type_choices': Activity.ActivityType.choices,
                'is_edit': True,
            })

        activity.title = request.POST.get('title')
        activity.code = request.POST.get('code')
        activity.description = request.POST.get('description')
        activity.activity_type = request.POST.get('activity_type')
        activity.start_time = request.POST.get('start_time')
        activity.end_time = request.POST.get('end_time')
        activity.location = request.POST.get('location')
        activity.organization = org
        activity.semester_id = request.POST.get('semester') or None
        activity.point_category_id = request.POST.get('point_category') or None
        activity.save()
        messages.success(request, 'Da cap nhat hoat dong thanh cong!')
        return redirect('activities:detail', pk=pk)

    context = {
        'activity': activity,
        'organizations': allowed_orgs,  # B1: filtered
        'semesters': Semester.objects.all().order_by('-start_date'),
        'point_categories': PointCategory.objects.filter(is_active=True).order_by('code'),
        'type_choices': Activity.ActivityType.choices,
        'is_edit': True,
    }
    return render(request, 'activities/form.html', context)


@login_required
def activity_delete(request, pk):
    """Delete activity (DRAFT only, STAFF/ADMIN with edit permission)."""
    activity = get_object_or_404(Activity, pk=pk)

    if activity.status != 'DRAFT':
        messages.error(request, 'Chi co the xoa hoat dong o trang thai Nhap.')
        return redirect('activities:detail', pk=pk)

    if not can_edit_activity(request.user, activity):
        messages.error(request, 'Ban khong co quyen xoa hoat dong nay.')
        return redirect('activities:detail', pk=pk)

    if request.method == 'POST':
        title = activity.title
        activity.delete()
        messages.success(request, f'Da xoa hoat dong "{title}".')
        return redirect('activities:list')

    return render(request, 'activities/confirm_delete.html', {'activity': activity})


@login_required
def activity_approve(request, pk):
    """
    Approve/submit a pending activity.
    B2: Parent Org Staff can approve Child Org activities.
    Flow:
      DRAFT -> PENDING  (Staff/creator submits for review)
      PENDING -> APPROVED  (Parent Staff or Admin approves)
    """
    activity = get_object_or_404(Activity, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action', 'submit')

        if action == 'submit' and activity.status == 'DRAFT':
            # Any Staff with edit permission can submit for review
            if can_edit_activity(request.user, activity):
                activity.status = Activity.ActivityStatus.PENDING
                activity.save()
                messages.success(request, 'Da gui hoat dong de phe duyet.')
            else:
                messages.error(request, 'Ban khong co quyen gui hoat dong nay.')

        elif action == 'approve' and activity.status == 'PENDING':
            # B2: Only parent staff or admin can approve
            if can_approve_activity(request.user, activity):
                activity.status = Activity.ActivityStatus.APPROVED
                activity.approved_by = request.user
                activity.approved_at = timezone.now()
                activity.save()
                messages.success(request, 'Da phe duyet hoat dong thanh cong!')
            else:
                messages.error(request, 'Ban khong co quyen phe duyet hoat dong nay.')

    return redirect('activities:detail', pk=pk)


@login_required
def activity_reject(request, pk):
    """
    Reject a pending activity back to DRAFT.
    B2: Only Parent Org Staff or Admin can reject.
    """
    activity = get_object_or_404(Activity, pk=pk)

    if request.method == 'POST' and activity.status == 'PENDING':
        # B2: Same approval permission is needed to reject
        if can_approve_activity(request.user, activity):
            activity.status = Activity.ActivityStatus.DRAFT
            activity.save()
            messages.success(request, 'Da tu choi. Hoat dong quay ve trang thai Nhap.')
        else:
            messages.error(request, 'Ban khong co quyen tu choi hoat dong nay.')

    return redirect('activities:detail', pk=pk)


@login_required
def activity_pending_list(request):
    """
    B2: List of activities pending approval.
    Staff: sees only child org activities they can approve.
    Admin: sees all pending activities.
    """
    if request.user.role == 'STUDENT':
        messages.error(request, 'Ban khong co quyen xem danh sach phe duyet.')
        return redirect('activities:list')

    if request.user.role == 'ADMIN':
        pending = Activity.objects.filter(status='PENDING').select_related('organization', 'created_by')
    else:
        # B2: Get child orgs this staff can approve for
        approvable_orgs = get_approvable_orgs(request.user)
        if not approvable_orgs.exists():
            pending = Activity.objects.none()
        else:
            pending = Activity.objects.filter(
                status='PENDING',
                organization__in=approvable_orgs,
            ).select_related('organization', 'created_by')

    context = {
        'pending_activities': pending.order_by('-created_at'),
        'total_pending': pending.count(),
    }
    return render(request, 'activities/pending_list.html', context)


@login_required
def activity_register(request, pk):
    """Student registers for an activity."""
    activity = get_object_or_404(Activity, pk=pk)

    if activity.status != 'APPROVED':
        messages.error(request, 'Chi co the dang ky hoat dong da duoc phe duyet.')
        return redirect('activities:detail', pk=pk)

    if request.method == 'POST':
        reg, created = ActivityRegistration.objects.get_or_create(
            activity=activity,
            student=request.user,
            defaults={'status': 'REGISTERED'},
        )
        if created:
            messages.success(request, 'Dang ky tham gia thanh cong!')
        else:
            messages.info(request, 'Ban da dang ky hoat dong nay roi.')

    return redirect('activities:detail', pk=pk)


@login_required
def activity_cancel_registration(request, pk):
    """Student cancels their registration."""
    activity = get_object_or_404(Activity, pk=pk)

    if request.method == 'POST':
        reg = ActivityRegistration.objects.filter(
            activity=activity, student=request.user, status='REGISTERED'
        ).first()
        if reg:
            reg.status = 'CANCELED'
            reg.save()
            messages.success(request, 'Da huy dang ky tham gia.')
        else:
            messages.error(request, 'Khong tim thay dang ky cua ban.')

    return redirect('activities:detail', pk=pk)
