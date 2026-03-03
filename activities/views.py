from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import Activity, ActivityRegistration, PointCategory
from core.models import Organization, Semester


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
    }
    return render(request, 'activities/detail.html', context)


@login_required
def activity_create(request):
    """Create a new activity (STAFF/ADMIN only)."""
    if request.user.role == 'STUDENT':
        messages.error(request, 'Ban khong co quyen tao hoat dong.')
        return redirect('activities:list')

    if request.method == 'POST':
        activity = Activity(
            title=request.POST.get('title'),
            code=request.POST.get('code'),
            description=request.POST.get('description'),
            activity_type=request.POST.get('activity_type'),
            start_time=request.POST.get('start_time'),
            end_time=request.POST.get('end_time'),
            location=request.POST.get('location'),
            organization_id=request.POST.get('organization'),
            semester_id=request.POST.get('semester') or None,
            point_category_id=request.POST.get('point_category') or None,
            created_by=request.user,
            status=Activity.ActivityStatus.DRAFT,
        )
        activity.save()
        messages.success(request, f'Da tao hoat dong "{activity.title}" thanh cong!')
        return redirect('activities:detail', pk=activity.pk)

    context = {
        'organizations': Organization.objects.filter(status=True),
        'semesters': Semester.objects.all().order_by('-start_date'),
        'point_categories': PointCategory.objects.filter(is_active=True).order_by('code'),
        'type_choices': Activity.ActivityType.choices,
    }
    return render(request, 'activities/form.html', context)


@login_required
def activity_edit(request, pk):
    """Edit activity (only DRAFT status)."""
    activity = get_object_or_404(Activity, pk=pk)

    if activity.status != 'DRAFT':
        messages.error(request, 'Chi co the chinh sua hoat dong o trang thai Nhap.')
        return redirect('activities:detail', pk=pk)

    if request.user.role == 'STUDENT':
        messages.error(request, 'Ban khong co quyen chinh sua hoat dong.')
        return redirect('activities:detail', pk=pk)

    if request.method == 'POST':
        activity.title = request.POST.get('title')
        activity.code = request.POST.get('code')
        activity.description = request.POST.get('description')
        activity.activity_type = request.POST.get('activity_type')
        activity.start_time = request.POST.get('start_time')
        activity.end_time = request.POST.get('end_time')
        activity.location = request.POST.get('location')
        activity.organization_id = request.POST.get('organization')
        activity.semester_id = request.POST.get('semester') or None
        activity.point_category_id = request.POST.get('point_category') or None
        activity.save()
        messages.success(request, 'Da cap nhat hoat dong thanh cong!')
        return redirect('activities:detail', pk=pk)

    context = {
        'activity': activity,
        'organizations': Organization.objects.filter(status=True),
        'semesters': Semester.objects.all().order_by('-start_date'),
        'point_categories': PointCategory.objects.filter(is_active=True).order_by('code'),
        'type_choices': Activity.ActivityType.choices,
        'is_edit': True,
    }
    return render(request, 'activities/form.html', context)


@login_required
def activity_delete(request, pk):
    """Delete activity (DRAFT only, STAFF/ADMIN)."""
    activity = get_object_or_404(Activity, pk=pk)

    if activity.status != 'DRAFT':
        messages.error(request, 'Chi co the xoa hoat dong o trang thai Nhap.')
        return redirect('activities:detail', pk=pk)

    if request.method == 'POST':
        title = activity.title
        activity.delete()
        messages.success(request, f'Da xoa hoat dong "{title}".')
        return redirect('activities:list')

    return render(request, 'activities/confirm_delete.html', {'activity': activity})


@login_required
def activity_approve(request, pk):
    """Approve a pending activity (ADMIN/STAFF)."""
    activity = get_object_or_404(Activity, pk=pk)

    if request.user.role == 'STUDENT':
        messages.error(request, 'Ban khong co quyen phe duyet hoat dong.')
        return redirect('activities:detail', pk=pk)

    if request.method == 'POST':
        if activity.status == 'DRAFT':
            activity.status = Activity.ActivityStatus.PENDING
            activity.save()
            messages.success(request, 'Da gui hoat dong de phe duyet.')
        elif activity.status == 'PENDING':
            activity.status = Activity.ActivityStatus.APPROVED
            activity.approved_by = request.user
            activity.approved_at = timezone.now()
            activity.save()
            messages.success(request, 'Da phe duyet hoat dong thanh cong!')

    return redirect('activities:detail', pk=pk)


@login_required
def activity_reject(request, pk):
    """Reject a pending activity back to DRAFT."""
    activity = get_object_or_404(Activity, pk=pk)

    if request.user.role == 'STUDENT':
        messages.error(request, 'Ban khong co quyen tu choi hoat dong.')
        return redirect('activities:detail', pk=pk)

    if request.method == 'POST' and activity.status == 'PENDING':
        activity.status = Activity.ActivityStatus.DRAFT
        activity.save()
        messages.success(request, 'Da tu choi hoat dong. Hoat dong da quay lai trang thai Nhap.')

    return redirect('activities:detail', pk=pk)


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
