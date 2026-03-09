from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Count, Q
from django.core.paginator import Paginator

from .models import Activity, ActivityParticipation, PointCategory
from core.models import Organization, Semester
from core.permissions import (
    can_create_activity, can_edit_activity, can_approve_activity,
    get_officer_orgs, get_approvable_orgs,
    get_point_category_orgs, can_manage_point_category, get_usable_point_category_orgs,
    group_orgs_by_root, get_manageable_orgs
)


@login_required
def activity_list(request):
    """List activities with filtering. STUDENT gets redirected to their own portal."""
    # Students should use their filtered portal, not the admin/staff list
    if request.user.role == 'STUDENT':
        return redirect('students:portal')

    qs = Activity.objects.select_related('organization', 'created_by', 'semester').annotate(
        pending_attendance_count=Count(
            'participations',
            filter=Q(participations__status='ATTENDED')
        ),
        registered_count=Count(
            'participations',
            filter=Q(participations__status='REGISTERED')
        )
    )

    if request.user.role != 'ADMIN':
        from core.permissions import get_usable_point_category_orgs
        visible_orgs = get_usable_point_category_orgs(request.user)
        qs = qs.filter(organization__in=visible_orgs)
        # Using visible_orgs as the base for the organization dropdown
        organizations = visible_orgs.order_by('name')
    else:
        organizations = Organization.objects.filter(status=True).order_by('name')

    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)

    activity_type = request.GET.get('type')
    if activity_type:
        qs = qs.filter(activity_type=activity_type)

    org_id = request.GET.get('org')
    if org_id:
        qs = qs.filter(organization_id=org_id)

    sem_id = request.GET.get('semester')
    if sem_id:
        qs = qs.filter(semester_id=sem_id)

    search = request.GET.get('q')
    if search:
        qs = qs.filter(title__icontains=search)
        
    qs = qs.order_by('-created_at')
    
    # Pagination (12 records per page)
    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'activities': page_obj,  # Pass the Pager instead
        'page_obj': page_obj,
        'status_choices': Activity.ActivityStatus.choices,
        'type_choices': Activity.ActivityType.choices,
        'organizations': organizations,
        'org_groups': group_orgs_by_root(organizations),
        'semesters': Semester.objects.all().order_by('-start_date'),
        'current_status': status or '',
        'current_type': activity_type or '',
        'current_org': org_id or '',
        'current_semester': sem_id or '',
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
    participations = activity.participations.select_related('student').order_by('-registered_at')

    # Check if current user is registered (only REGISTERED status, not CANCELED)
    user_registration = None
    if request.user.role == 'STUDENT':
        user_registration = activity.participations.filter(
            student=request.user, status='REGISTERED'
        ).first()

    # D3: Budget info
    budget = activity.budget_info

    context = {
        'activity': activity,
        'registrations': participations,
        'user_registration': user_registration,
        'registration_count': participations.filter(status='REGISTERED').count(),
        # B1/B2 permission flags - used in template to show/hide buttons
        'can_edit': can_edit_activity(request.user, activity),
        'can_approve': can_approve_activity(request.user, activity),
        # D3: Budget tab
        'budget': budget,
        'budget_items_count': len(budget.get('items', [])) if budget else 0,
        'can_manage_budget': request.user.role != 'STUDENT' and can_edit_activity(request.user, activity),
    }
    return render(request, 'activities/detail.html', context)


@login_required
def activity_create(request):
    """Create a new activity (STAFF/ADMIN only).
    B1: Staff can only select orgs they are officer of.
    """
    if request.user.role == 'STUDENT':
        messages.error(request, 'Bạn không có quyền tạo hoạt động.')
        return redirect('activities:list')

    # B1: Get only the orgs this user can create activities for
    allowed_orgs = get_officer_orgs(request.user)

    if request.method == 'POST':
        org_id = request.POST.get('organization')
        org = Organization.objects.filter(pk=org_id, status=True).first()

        # B1: Verify the submitted org is actually allowed
        if not org or not can_create_activity(request.user, org):
            messages.error(request, 'Bạn không có quyền tạo hoạt động cho tổ chức này.')
            return render(request, 'activities/form.html', {
                'organizations': allowed_orgs,
                'org_groups': group_orgs_by_root(allowed_orgs),
                'semesters': Semester.objects.filter(organization__in=get_point_category_orgs(request.user)).order_by('-start_date'),
                # Load all active categories from allowed orgs for the dropdown
                'point_categories': PointCategory.objects.filter(
                    is_active=True,
                    organization__in=get_point_category_orgs(request.user),
                ).select_related('organization').order_by('organization__name', 'code'),
                'type_choices': Activity.ActivityType.choices,
            })

        # Parse max_participants (empty string -> None meaning unlimited)
        max_p_raw = request.POST.get('max_participants', '').strip()
        max_p = int(max_p_raw) if max_p_raw.isdigit() else None

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
            points=request.POST.get('points') or 0,
            max_participants=max_p,
            created_by=request.user,
            status=Activity.ActivityStatus.DRAFT,
        )
        activity.save()
        messages.success(request, f'Đã tạo hoạt động "{activity.title}" thành công!')
        return redirect('activities:detail', pk=activity.pk)

    context = {
        'organizations': allowed_orgs,  # B1: filtered list
        'org_groups': group_orgs_by_root(allowed_orgs),
        'semesters': Semester.objects.filter(organization__in=get_point_category_orgs(request.user)).order_by('-start_date'),
        'point_categories': PointCategory.objects.filter(
            is_active=True,
            organization__in=get_usable_point_category_orgs(request.user),
        ).select_related('organization').order_by('organization__name', 'code'),
        'type_choices': Activity.ActivityType.choices,
    }
    return render(request, 'activities/form.html', context)


@login_required
def activity_edit(request, pk):
    """Edit activity (only DRAFT status, with B1 permission check)."""
    activity = get_object_or_404(Activity, pk=pk)

    if activity.status != 'DRAFT':
        messages.error(request, 'Chỉ có thể chỉnh sửa hoạt động ở trạng thái Nháp.')
        return redirect('activities:detail', pk=pk)

    # B1: Check edit permission
    if not can_edit_activity(request.user, activity):
        messages.error(request, 'Bạn không có quyền chỉnh sửa hoạt động này.')
        return redirect('activities:detail', pk=pk)

    # B1: Staff only sees their own orgs, Admin sees all
    allowed_orgs = get_officer_orgs(request.user)

    if request.method == 'POST':
        org_id = request.POST.get('organization')
        org = Organization.objects.filter(pk=org_id, status=True).first()

        # B1: Verify the submitted org is actually allowed
        if not org or not can_create_activity(request.user, org):
            messages.error(request, 'Bạn không có quyền gán hoạt động cho tổ chức này.')
            return render(request, 'activities/form.html', {
                'activity': activity,
                'organizations': allowed_orgs,
                'org_groups': group_orgs_by_root(allowed_orgs),
                'semesters': Semester.objects.filter(organization__in=get_point_category_orgs(request.user)).order_by('-start_date'),
                'point_categories': PointCategory.objects.filter(
                    is_active=True,
                    organization__in=get_usable_point_category_orgs(request.user),
                ).select_related('organization').order_by('organization__name', 'code'),
                'type_choices': Activity.ActivityType.choices,
                'is_edit': True,
            })

        # Parse max_participants (empty string -> None meaning unlimited)
        max_p_raw = request.POST.get('max_participants', '').strip()
        max_p = int(max_p_raw) if max_p_raw.isdigit() else None

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
        activity.points = request.POST.get('points') or 0
        activity.max_participants = max_p
        activity.save()
        messages.success(request, 'Đã cập nhật hoạt động thành công!')
        return redirect('activities:detail', pk=pk)

    context = {
        'activity': activity,
        'organizations': allowed_orgs,  # B1: filtered
        'org_groups': group_orgs_by_root(allowed_orgs),
        'semesters': Semester.objects.filter(organization__in=get_point_category_orgs(request.user)).order_by('-start_date'),
        'point_categories': PointCategory.objects.filter(
            is_active=True,
            organization__in=get_usable_point_category_orgs(request.user),
        ).select_related('organization').order_by('organization__name', 'code'),
        'type_choices': Activity.ActivityType.choices,
        'is_edit': True,
    }
    return render(request, 'activities/form.html', context)


@login_required
def activity_delete(request, pk):
    """Delete activity (DRAFT only, STAFF/ADMIN with edit permission)."""
    activity = get_object_or_404(Activity, pk=pk)

    if activity.status != 'DRAFT':
        messages.error(request, 'Chỉ có thể xóa hoạt động ở trạng thái Nháp.')
        return redirect('activities:detail', pk=pk)

    if not can_edit_activity(request.user, activity):
        messages.error(request, 'Bạn không có quyền xóa hoạt động này.')
        return redirect('activities:detail', pk=pk)

    if request.method == 'POST':
        title = activity.title
        activity.delete()
        messages.success(request, f'Đã xóa hoạt động "{title}".')
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
                messages.success(request, 'Đã gửi hoạt động để phê duyệt.')
            else:
                messages.error(request, 'Bạn không có quyền gửi hoạt động này.')

        elif action == 'approve' and activity.status == 'PENDING':
            # B2: Only parent staff or admin can approve
            if can_approve_activity(request.user, activity):
                activity.status = Activity.ActivityStatus.APPROVED
                activity.approved_by = request.user
                activity.approved_at = timezone.now()
                activity.save()
                messages.success(request, 'Đã phê duyệt hoạt động thành công!')
            else:
                messages.error(request, 'Bạn không có quyền phê duyệt hoạt động này.')

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
            messages.success(request, 'Đã từ chối. Hoạt động quay về trạng thái Nháp.')
        else:
            messages.error(request, 'Bạn không có quyền từ chối hoạt động này.')

    return redirect('activities:detail', pk=pk)


@login_required
def activity_pending_list(request):
    """
    B2: List of activities pending approval.
    Staff: sees only child org activities they can approve.
    Admin: sees all pending activities.
    """
    if request.user.role == 'STUDENT':
        messages.error(request, 'Bạn không có quyền xem danh sách phê duyệt.')
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
        messages.error(request, 'Chỉ có thể đăng ký hoạt động đã được phê duyệt.')
        return redirect('activities:detail', pk=pk)

    if request.method == 'POST':
        # Check slot limit before registering
        if activity.max_participants is not None:
            current_count = activity.participations.filter(status='REGISTERED').count()
            if current_count >= activity.max_participants:
                messages.error(
                    request,
                    f'Hoạt động đã đủ số lượng đăng ký tối đa ({activity.max_participants} người). Rất tiếc bạn không thể đăng ký tham gia lúc này.'
                )
                return redirect('activities:detail', pk=pk)

        reg, created = ActivityParticipation.objects.get_or_create(
            activity=activity,
            student=request.user,
            defaults={'status': 'REGISTERED'},
        )
        if not created and reg.status == 'CANCELED':
            # Re-register (was previously canceled) - check slot again counted above
            reg.status = 'REGISTERED'
            reg.save()
            messages.success(request, 'Đăng ký tham gia thành công!')
        elif created:
            messages.success(request, 'Đăng ký tham gia thành công!')
        else:
            messages.info(request, 'Bạn đã đăng ký hoạt động này rồi.')

    return redirect('activities:detail', pk=pk)


@login_required
def activity_cancel_registration(request, pk):
    """Student cancels their registration."""
    activity = get_object_or_404(Activity, pk=pk)

    if request.method == 'POST':
        reg = ActivityParticipation.objects.filter(
            activity=activity, student=request.user, status='REGISTERED'
        ).first()
        if reg:
            reg.status = 'CANCELED'
            reg.save()
            messages.success(request, 'Đã huỷ đăng ký tham gia.')
        else:
            messages.error(request, 'Không tìm thấy đăng ký của bạn.')

    return redirect('activities:detail', pk=pk)


# ─── PHASE C: Student Portal ──────────────────────────────────────────────────

def _get_activity_time_status(activity, now):
    """
    C1: Return time-based display status for students.
    Ignores internal DRAFT/PENDING, shows meaningful status.
    """
    if activity.end_time and activity.end_time < now:
        return 'ENDED', 'Đã kết thúc'
    if activity.start_time and activity.start_time <= now:
        return 'ONGOING', 'Đang diễn ra'
    return 'UPCOMING', 'Sắp diễn ra'


def _get_student_visible_orgs(user):
    """
    C1: Get all org IDs a student can see activities for:

    Priority order:
    1. OrganizationMember records (created by Import Excel / manual assignment)
       → the student can see activities from any org they are a member of,
         AND activities from all ANCESTOR orgs in the chain (e.g. faculty sees school).
    2. Fallback (if student has no OrganizationMember at all):
       Try to match StudentProfile.faculty by name against UNION_FACULTY orgs.
       This supports students who self-registered without being imported.
    """
    from core.models import OrganizationMember
    org_ids = set()

    # 1. All orgs the student is a member of (primary mechanism via Import Excel)
    member_org_ids = list(
        OrganizationMember.objects.filter(user=user).values_list('organization_id', flat=True)
    )

    if member_org_ids:
        org_ids.update(member_org_ids)

        # Also walk up the ancestor chain for each member org so that
        # "Sinh viên của Đoàn khoa CNTT" also sees activities from Đoàn trường
        # (already included from step 1), but this ensures any intermediate orgs
        # in the tree are also included.
        member_orgs = Organization.objects.filter(id__in=member_org_ids, status=True).select_related('parent')
        for org in member_orgs:
            parent = org.parent
            while parent is not None:
                org_ids.add(parent.id)
                parent = parent.parent

    else:
        # 3. Fallback: match by StudentProfile.faculty name (for self-registered students)
        try:
            profile = user.student_profile
            faculty_name = profile.faculty
            if faculty_name:
                fallback_orgs = Organization.objects.filter(
                    status=True,
                    type__in=[
                        Organization.OrgType.UNION_FACULTY,
                        Organization.OrgType.CLASS,
                    ],
                    name__icontains=faculty_name,
                )
                org_ids.update(fallback_orgs.values_list('id', flat=True))
                # Include their parent orgs too
                for org in fallback_orgs:
                    if org.parent:
                        org_ids.add(org.parent.id)
        except Exception:
            pass

    return org_ids


@login_required
def student_activity_list(request):
    """
    C1: Student activity portal.
    - Only shows APPROVED/ONGOING/DONE activities (no DRAFT/PENDING)
    - Filters by student's org visibility
    - Status shown as time-based: Sắp diễn ra / Đang diễn ra / Đã kết thúc
    C2: Detects active AttendanceSession to decide check-in availability
    """
    now = timezone.now()

    # C1: Filter base queryset - only published activities
    qs = Activity.objects.filter(
        status__in=['APPROVED', 'ONGOING', 'DONE']
    ).select_related('organization', 'semester', 'point_category').order_by('start_time')

    # C1: Filter by student's visible orgs (only for STUDENT role)
    if request.user.role == 'STUDENT':
        visible_org_ids = _get_student_visible_orgs(request.user)
        if visible_org_ids:
            qs = qs.filter(organization_id__in=visible_org_ids)
        else:
            qs = qs.none()

    # Filter: time-based status tab
    time_filter = request.GET.get('time', 'upcoming')
    if time_filter == 'upcoming':
        display_qs = qs.filter(start_time__gt=now)
    elif time_filter == 'ongoing':
        display_qs = qs.filter(start_time__lte=now, end_time__gte=now)
    elif time_filter == 'ended':
        display_qs = qs.filter(end_time__lt=now).order_by('-end_time')
    else:
        display_qs = qs

    # Search
    search = request.GET.get('q', '').strip()
    if search:
        display_qs = display_qs.filter(title__icontains=search)

    # Annotate each activity with time-based status and active session
    from attendance.models import AttendanceSession
    activities_data = []
    for act in display_qs:
        time_status, time_label = _get_activity_time_status(act, now)

        # C2: Check if there's an OPEN AttendanceSession in the current time window
        active_session = act.attendance_sessions.filter(
            status='OPEN',
            start_time__lte=now,
            end_time__gte=now,
        ).first()

        # Check if student already checked in for this session
        already_checkedin = False
        if active_session and request.user.is_authenticated:
            already_checkedin = active_session.records.filter(
                student=request.user
            ).exists()

        activities_data.append({
            'activity': act,
            'time_status': time_status,
            'time_label': time_label,
            'active_session': active_session,
            'already_checkedin': already_checkedin,
        })

    context = {
        'activities_data': activities_data,
        'time_filter': time_filter,
        'search_query': search,
        'now': now,
        'upcoming_count': qs.filter(start_time__gt=now).count(),
        'ongoing_count': qs.filter(start_time__lte=now, end_time__gte=now).count(),
        'ended_count': qs.filter(end_time__lt=now).count(),
    }
    return render(request, 'activities/student_list.html', context)


@login_required
def student_dashboard(request):
    """
    C3: Student personal dashboard.
    - Total attendance count (VERIFIED)
    - Attendance history table with activity, point category, status
    - Summary by point category
    """
    from activities.models import ActivityParticipation

    # All attendance records for this student
    records = ActivityParticipation.objects.filter(
        student=request.user,
        checkin_time__isnull=False
    ).select_related(
        'attendance_session',
        'attendance_session__activity',
        'attendance_session__activity__point_category',
        'verified_by',
    ).order_by('-checkin_time')

    # Aggregate stats
    total_checkins = records.count()
    verified_count = records.filter(status='VERIFIED').count()
    pending_count = records.filter(status='ATTENDED').count()
    rejected_count = records.filter(status__in=['ABSENT', 'CANCELED', 'BANNED']).count()

    # Group by point category for summary
    from django.db.models import Count
    category_summary = {}
    for record in records.filter(status='VERIFIED'):
        cat = record.activity.point_category if record.activity else None
        cat_name = cat.name if cat else 'Không phân loại'
        cat_code = cat.code if cat else '-'
        if cat_name not in category_summary:
            category_summary[cat_name] = {'code': cat_code, 'count': 0}
        category_summary[cat_name]['count'] += 1

    # Student profile
    try:
        profile = request.user.student_profile
    except Exception:
        profile = None

    context = {
        'records': records[:50],  # latest 50
        'total_checkins': total_checkins,
        'verified_count': verified_count,
        'pending_count': pending_count,
        'rejected_count': rejected_count,
        'category_summary': category_summary,
        'profile': profile,
    }
    return render(request, 'activities/student_dashboard.html', context)


# ─── PHASE D: Budget Management ───────────────────────────────────────────────

def _can_manage_budget(user, activity):
    if user.role == 'ADMIN': return True
    return can_edit_activity(user, activity)

def _can_approve_budget(user, activity):
    if user.role == 'ADMIN': return True
    return can_approve_activity(user, activity)

@login_required
def budget_detail(request, activity_pk):
    activity = get_object_or_404(Activity, pk=activity_pk)
    if not _can_manage_budget(request.user, activity) and not _can_approve_budget(request.user, activity):
        messages.error(request, 'Bạn không thể xem ngân sách.')
        return redirect('activities:detail', pk=activity.pk)

    budget = activity.budget_info or {}
    items = budget.get('items', [])
    for i, it in enumerate(items):
        it['item_index'] = i

    context = {
        'activity': activity,
        'budget': budget,
        'budget_items': items,
        'can_manage': _can_manage_budget(request.user, activity),
        'can_edit': _can_manage_budget(request.user, activity) and budget.get('status') in [None, 'DRAFT', 'REJECTED'],
        'can_approve': _can_approve_budget(request.user, activity) and budget.get('status') == 'PENDING',
    }
    return render(request, 'activities/budget_detail.html', context)

@login_required
def budget_create(request, activity_pk):
    activity = get_object_or_404(Activity, pk=activity_pk)
    if not _can_manage_budget(request.user, activity): return redirect('activities:detail', pk=activity.pk)
    
    if not activity.budget_info:
        activity.budget_info = {'status': 'DRAFT', 'total_amount': 0.0, 'description': '', 'items': []}
        activity.save(update_fields=['budget_info'])
    return redirect('activities:budget_detail', activity_pk=activity.pk)

@login_required
def budget_add_item(request, activity_pk):
    activity = get_object_or_404(Activity, pk=activity_pk)
    if not _can_manage_budget(request.user, activity): return redirect('activities:detail', pk=activity.pk)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        amount_str = request.POST.get('amount', '0').replace(',', '')
        try:
            amount = float(amount_str)
        except:
            amount = 0.0
            
        if name and amount >= 0:
            budget = activity.budget_info or {'status': 'DRAFT', 'items': [], 'total_amount': 0}
            budget.setdefault('items', []).append({
                'name': name,
                'amount': amount,
                'category': request.POST.get('category', '').strip(),
                'note': request.POST.get('note', '').strip()
            })
            budget['total_amount'] = sum(float(i.get('amount', 0)) for i in budget['items'])
            activity.budget_info = budget
            activity.save(update_fields=['budget_info'])
            messages.success(request, 'Đã thêm khoản chi.')
    return redirect('activities:budget_detail', activity_pk=activity.pk)

@login_required
def budget_delete_item(request, activity_pk, item_pk):
    activity = get_object_or_404(Activity, pk=activity_pk)
    if not _can_manage_budget(request.user, activity): return redirect('activities:detail', pk=activity.pk)

    if request.method == 'POST':
        budget = activity.budget_info
        if budget and 'items' in budget:
            try:
                budget['items'].pop(item_pk)
                budget['total_amount'] = sum(float(i.get('amount', 0)) for i in budget['items'])
                activity.budget_info = budget
                activity.save(update_fields=['budget_info'])
                messages.success(request, 'Đã xóa khoản chi.')
            except IndexError:
                pass
    return redirect('activities:budget_detail', activity_pk=activity.pk)

@login_required
def budget_submit(request, activity_pk):
    activity = get_object_or_404(Activity, pk=activity_pk)
    if not _can_manage_budget(request.user, activity): return redirect('activities:detail', pk=activity.pk)

    if request.method == 'POST':
        budget = activity.budget_info
        if budget:
            budget['status'] = 'PENDING'
            activity.budget_info = budget
            activity.save(update_fields=['budget_info'])
            messages.success(request, 'Đã trình duyệt ngân sách.')
    return redirect('activities:budget_detail', activity_pk=activity.pk)

@login_required
def budget_approve(request, activity_pk):
    activity = get_object_or_404(Activity, pk=activity_pk)
    if not _can_approve_budget(request.user, activity): return redirect('activities:budget_detail', activity_pk=activity.pk)

    if request.method == 'POST':
        budget = activity.budget_info
        if budget:
            budget['status'] = 'APPROVED'
            budget['approved_by'] = request.user.id
            activity.budget_info = budget
            activity.save(update_fields=['budget_info'])
            messages.success(request, 'Đã duyệt ngân sách.')
    return redirect('activities:budget_detail', activity_pk=activity.pk)

@login_required
def budget_reject(request, activity_pk):
    activity = get_object_or_404(Activity, pk=activity_pk)
    if not _can_approve_budget(request.user, activity): return redirect('activities:budget_detail', activity_pk=activity.pk)

    if request.method == 'POST':
        budget = activity.budget_info
        if budget:
            budget['status'] = 'REJECTED'
            activity.budget_info = budget
            activity.save(update_fields=['budget_info'])
            messages.warning(request, 'Đã từ chối ngân sách.')
    return redirect('activities:budget_detail', activity_pk=activity.pk)

# ─── POINT CATEGORY CRUD ────────────────────────────────────────────────────────

from django.db import models as dj_models


@login_required
def point_category_list(request):
    """
    List PointCategories scoped to user's org(s).
    - ADMIN: sees all root orgs, can filter.
    - STAFF: sees root org they belong to.
    - STUDENT: access denied.
    """
    if request.user.role == 'STUDENT':
        messages.error(request, 'Bạn không có quyền quản lý danh mục điểm.')
        return redirect('activities:list')

    manageable_orgs = get_point_category_orgs(request.user)

    # Handle Filters
    selected_school_id = request.GET.get('school', '')
    selected_org_id = request.GET.get('org', '')
    status_filter = request.GET.get('status', '')
    search = request.GET.get('q', '').strip()

    categories = PointCategory.objects.filter(
        organization__in=manageable_orgs
    ).select_related('organization').order_by('organization__name', 'code')

    if search:
        categories = categories.filter(
            dj_models.Q(name__icontains=search) | dj_models.Q(code__icontains=search)
        )
    if status_filter == 'active':
        categories = categories.filter(is_active=True)
    elif status_filter == 'inactive':
        categories = categories.filter(is_active=False)

    from core.permissions import get_root_org, get_officer_orgs
    from core.models import Organization
    
    root_orgs = []
    filtered_orgs = []
    user_org = None
    
    if request.user.role == 'ADMIN':
        all_orgs = list(manageable_orgs.select_related('parent', 'parent__parent'))
        root_org_map = {}
        for org in all_orgs:
            root = get_root_org(org)
            if root.id not in root_org_map:
                root_org_map[root.id] = root
            
            # Populate filtered_orgs if no school selected, or if belongs to selected school
            if not selected_school_id or str(root.id) == selected_school_id:
                filtered_orgs.append(org)
                
        root_orgs = list(root_org_map.values())
        
        # Apply filters
        if selected_org_id:
            categories = categories.filter(organization_id=selected_org_id)
        elif selected_school_id:
            # Get all categories belonging to any org under this school
            school_org_ids = [org.id for org in filtered_orgs]
            categories = categories.filter(organization_id__in=school_org_ids)
            
    else:
        user_org = get_officer_orgs(request.user).first()
        
    # Group categories by organization for accordion display
    from collections import OrderedDict
    org_groups = OrderedDict()
    
    for cat in categories:
        org_id = cat.organization_id
        if org_id not in org_groups:
            org_groups[org_id] = {
                'organization': cat.organization,
                'categories': [],
                'has_active': False
            }
        
        org_groups[org_id]['categories'].append(cat)
        if cat.is_active:
            org_groups[org_id]['has_active'] = True
            
    grouped_categories = list(org_groups.values())

    context = {
        'grouped_categories': grouped_categories,
        'categories_count': categories.count(),
        'manageable_orgs': manageable_orgs,
        'root_orgs': root_orgs,
        'filtered_orgs': filtered_orgs,
        'user_org': user_org,
        'selected_school_id': selected_school_id,
        'selected_org_id': selected_org_id,
        'search_query': search,
        'is_admin': request.user.role == 'ADMIN',
    }
    return render(request, 'activities/point_category_list.html', context)


@login_required
def point_category_create(request):
    """
    Create a new PointCategory.
    STAFF: org is auto-set to their root org.
    ADMIN: must choose an org from the dropdown.
    """
    if request.user.role == 'STUDENT':
        messages.error(request, 'Bạn không có quyền tạo danh mục điểm.')
        return redirect('activities:list')

    manageable_orgs = get_point_category_orgs(request.user)
    if not manageable_orgs.exists():
        messages.error(request, 'Bạn không thuộc tổ chức nào để tạo danh mục điểm.')
        return redirect('point_categories:point_category_list')

    from core.permissions import get_root_org, get_officer_orgs
    admin_org_groups = {}
    user_org = None
    
    if request.user.role == 'ADMIN':
        all_orgs = list(manageable_orgs.select_related('parent', 'parent__parent'))
        for org in all_orgs:
            root = get_root_org(org)
            if root.name not in admin_org_groups:
                admin_org_groups[root.name] = []
            admin_org_groups[root.name].append(org)
    else:
        user_org = get_officer_orgs(request.user).first()

    if request.method == 'POST':
        if request.user.role == 'ADMIN':
            org_id = request.POST.get('organization')
            org = manageable_orgs.filter(pk=org_id).first()
        else:
            org = user_org
            
        if not org:
            messages.error(request, 'Tổ chức không hợp lệ hoặc bạn không có quyền.')
        else:
            code = request.POST.get('code', '').strip().upper()
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            is_active = request.POST.get('is_active') == 'on'

            if not code or not name:
                messages.error(request, 'Mã và Tên danh mục là bắt buộc.')
            elif PointCategory.objects.filter(organization=org, code=code).exists():
                messages.error(request, f'Mã "{code}" đã tồn tại trong tổ chức này.')
            else:
                pc = PointCategory.objects.create(
                    organization=org,
                    code=code,
                    name=name,
                    description=description or None,
                    is_active=is_active,
                )
                messages.success(request, f'Đã tạo danh mục điểm "{pc}" thành công!')
                return redirect('point_categories:point_category_list')

    initial_org_id = request.GET.get('org', '')

    context = {
        'manageable_orgs': manageable_orgs,
        'admin_org_groups': admin_org_groups,
        'user_org': user_org,
        'is_admin': request.user.role == 'ADMIN',
        'POST': request.POST if request.method == 'POST' else {'organization': initial_org_id},
        'is_active_default': True,  # new categories are active by default
    }
    return render(request, 'activities/point_category_form.html', context)


@login_required
def point_category_edit(request, pk):
    """Edit an existing PointCategory (org cannot be changed)."""
    pc = get_object_or_404(PointCategory.objects.select_related('organization'), pk=pk)

    if not can_manage_point_category(request.user, pc):
        messages.error(request, 'Bạn không có quyền chỉnh sửa danh mục điểm này.')
        return redirect('point_categories:point_category_list')

    manageable_orgs = get_point_category_orgs(request.user)

    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        if not code or not name:
            messages.error(request, 'Mã và Tên danh mục là bắt buộc.')
        elif PointCategory.objects.filter(organization=pc.organization, code=code).exclude(pk=pk).exists():
            messages.error(request, f'Mã "{code}" đã tồn tại trong tổ chức này.')
        else:
            pc.code = code
            pc.name = name
            pc.description = description or None
            pc.is_active = is_active
            pc.save()
            messages.success(request, f'Đã cập nhật danh mục điểm "{pc}".')
            return redirect('point_categories:point_category_list')

    context = {
        'pc': pc,
        'manageable_orgs': manageable_orgs,
        'is_edit': True,
        'is_admin': request.user.role == 'ADMIN',
        'is_active_default': pc.is_active,  # carry current value for checkbox
    }
    return render(request, 'activities/point_category_form.html', context)


@login_required
def point_category_delete(request, pk):
    """
    Delete a PointCategory.
    If already used by any Activity → soft-delete (is_active=False) to preserve history.
    If not used → hard delete.
    """
    pc = get_object_or_404(PointCategory.objects.select_related('organization'), pk=pk)

    if not can_manage_point_category(request.user, pc):
        messages.error(request, 'Bạn không có quyền xóa danh mục điểm này.')
        return redirect('point_categories:point_category_list')

    if request.method == 'POST':
        in_use_count = pc.activities.count()
        if in_use_count > 0:
            pc.is_active = False
            pc.save(update_fields=['is_active'])
            messages.warning(
                request,
                f'Danh mục "{pc.name}" đang được dùng bởi {in_use_count} hoạt động. '
                f'Đã ẩn danh mục thay vì xóa để giữ lịch sử.'
            )
        else:
            name = str(pc)
            pc.delete()
            messages.success(request, f'Đã xóa danh mục điểm "{name}".')
        return redirect('point_categories:point_category_list')

    context = {
        'pc': pc,
        'in_use': pc.activities.exists(),
        'activity_count': pc.activities.count(),
    }
    return render(request, 'activities/point_category_confirm_delete.html', context)

