import base64
import io
import uuid

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from activities.models import Activity
from django.db.models import Count, Q
from .models import ActivityPoint, AttendanceRecord, AttendanceSession


# ────────────────────────────────────────────────────────────
# HELPER: Generate QR as base64 data URI
# ────────────────────────────────────────────────────────────
def _qr_base64(data: str) -> str:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1e3a8a", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


# ────────────────────────────────────────────────────────────
# SESSIONS
# ────────────────────────────────────────────────────────────
@login_required
def sessions_view(request):
    """List attendance sessions."""
    if request.user.role in ('ADMIN', 'STAFF'):
        qs = AttendanceSession.objects.select_related('activity')
    else:
        # Students see open sessions of activities they registered
        registered_ids = request.user.registrations.values_list('activity_id', flat=True)
        qs = AttendanceSession.objects.filter(
            activity_id__in=registered_ids,
            status=AttendanceSession.SessionStatus.OPEN,
        ).select_related('activity')

    context = {
        'sessions': qs.order_by('-created_at'),
        'now': timezone.now(),
    }
    return render(request, 'attendance/sessions.html', context)


@login_required
def activity_sessions_list(request, activity_pk):
    """List attendance sessions scoped to a specific activity."""
    activity = get_object_or_404(Activity, pk=activity_pk)
    qs = AttendanceSession.objects.filter(activity=activity).order_by('-created_at')
    
    # Students see only open sessions if they are registered
    if request.user.role == 'STUDENT':
        is_registered = request.user.registrations.filter(activity=activity).exists()
        if not is_registered:
            messages.error(request, "Bạn chưa đăng ký hoạt động này.")
            return redirect('activities:list')
        qs = qs.filter(status=AttendanceSession.SessionStatus.OPEN)
        
    context = {
        'activity': activity,
        'sessions': qs,
        'now': timezone.now(),
        'active_tab': 'sessions',
    }
    return render(request, 'attendance/activity_sessions.html', context)


@login_required
def session_create(request, activity_pk):
    """Create a new attendance session scoped to an activity (STAFF/ADMIN only)."""
    activity = get_object_or_404(Activity, pk=activity_pk)
    if request.user.role == 'STUDENT':
        messages.error(request, 'Bạn không có quyền tạo phiên điểm danh.')
        return redirect('attendance:activity_sessions', activity_pk=activity.pk)

    if request.method == 'POST':
        start_time_str = request.POST.get('start_time')
        end_time_str = request.POST.get('end_time')

        # Convert to datetime for validation
        from django.utils.dateparse import parse_datetime
        from datetime import timedelta
        from django.utils import timezone
        
        start_time_dt = parse_datetime(start_time_str)
        end_time_dt = parse_datetime(end_time_str)
        
        # Make timezone-aware if parsed successfully and naive
        if start_time_dt and timezone.is_naive(start_time_dt):
            start_time_dt = timezone.make_aware(start_time_dt)
        if end_time_dt and timezone.is_naive(end_time_dt):
            end_time_dt = timezone.make_aware(end_time_dt)

        # Basic validations
        if not start_time_dt or not end_time_dt:
            messages.error(request, 'Định dạng thời gian không hợp lệ.')
            return redirect('attendance:session_create', activity_pk=activity.pk)

        if end_time_dt <= start_time_dt:
            messages.error(request, 'Thời gian kết thúc phải diễn ra sau thời gian bắt đầu.')
            return redirect('attendance:session_create', activity_pk=activity.pk)

        # Business logic validation
        if start_time_dt < activity.start_time:
            messages.error(request, 'Thời gian bắt đầu phiên không được trước khi sự kiện diễn ra.')
            return redirect('attendance:session_create', activity_pk=activity.pk)

        if end_time_dt > activity.end_time + timedelta(hours=24):
            messages.error(request, 'Không thể kéo dài phiên quá 24 giờ sau khi sự kiện kết thúc.')
            return redirect('attendance:session_create', activity_pk=activity.pk)

        session = AttendanceSession(
            activity=activity,
            name=request.POST.get('name'),
            start_time=start_time_str,
            end_time=end_time_str,
            requires_photo=request.POST.get('requires_photo') == 'on',
            qr_token=uuid.uuid4().hex,
            status=AttendanceSession.SessionStatus.OPEN,
        )
        session.save()
        messages.success(request, f'Phiên điểm danh "{session.name}" đã được tạo!')
        return redirect('attendance:session_detail', pk=session.pk)

    return render(request, 'attendance/session_form.html', {'activity': activity})


@login_required
def session_detail(request, pk):
    """View session details and its records."""
    session = get_object_or_404(
        AttendanceSession.objects.select_related('activity'),
        pk=pk,
    )
    records = session.records.select_related('student', 'verified_by').order_by('-checkin_time')
    checkin_url = request.build_absolute_uri(f'/attendance/checkin/{session.qr_token}/')
    qr_data = _qr_base64(checkin_url)

    context = {
        'session': session,
        'records': records,
        'checkin_url': checkin_url,
        'qr_data': qr_data,
        'approved_count': records.filter(status='VERIFIED').count(),
        'pending_count': records.filter(status='PENDING').count(),
        'rejected_count': records.filter(status='REJECTED').count(),
        'now': timezone.now(),
    }
    return render(request, 'attendance/session_detail.html', context)


@login_required
def session_edit(request, pk):
    """Edit an existing attendance session (STAFF/ADMIN only)."""
    if request.user.role == 'STUDENT':
        messages.error(request, 'Bạn không có quyền chỉnh sửa phiên điểm danh.')
        return redirect('attendance:sessions')

    session = get_object_or_404(AttendanceSession, pk=pk)

    if request.method == 'POST':
        activity_id = request.POST.get('activity')
        start_time_str = request.POST.get('start_time')
        end_time_str = request.POST.get('end_time')

        # Convert to datetime for validation
        from django.utils.dateparse import parse_datetime
        from datetime import timedelta
        from django.utils import timezone
        
        start_time_dt = parse_datetime(start_time_str)
        end_time_dt = parse_datetime(end_time_str)
        
        # Make timezone-aware if parsed successfully and naive
        if start_time_dt and timezone.is_naive(start_time_dt):
            start_time_dt = timezone.make_aware(start_time_dt)
        if end_time_dt and timezone.is_naive(end_time_dt):
            end_time_dt = timezone.make_aware(end_time_dt)
            
        activity = get_object_or_404(Activity, pk=activity_id)

        # Basic validations
        if not start_time_dt or not end_time_dt:
            messages.error(request, 'Định dạng thời gian không hợp lệ.')
            return redirect('attendance:session_edit', pk=session.pk)

        if end_time_dt <= start_time_dt:
            messages.error(request, 'Thời gian kết thúc phải diễn ra sau thời gian bắt đầu.')
            return redirect('attendance:session_edit', pk=session.pk)

        # Business logic validation
        if start_time_dt < activity.start_time:
            messages.error(request, 'Thời gian bắt đầu phiên không được trước khi sự kiện diễn ra.')
            return redirect('attendance:session_edit', pk=session.pk)

        if end_time_dt > activity.end_time + timedelta(hours=24):
            messages.error(request, 'Không thể kéo dài phiên quá 24 giờ sau khi sự kiện kết thúc.')
            return redirect('attendance:session_edit', pk=session.pk)

        session.activity = activity
        session.name = request.POST.get('name')
        session.start_time = start_time_str
        session.end_time = end_time_str
        session.requires_photo = request.POST.get('requires_photo') == 'on'
        
        # If admin edits, we assume they are re-opening or extending it
        # Setting status back to OPEN ensures it works if it was manually closed before.
        session.status = AttendanceSession.SessionStatus.OPEN
        session.save()
        
        messages.success(request, f'Thông tin phiên "{session.name}" đã được cập nhật!')
        return redirect('attendance:session_detail', pk=session.pk)

    activities = Activity.objects.filter(status__in=['APPROVED', 'ONGOING']).order_by('-start_time')
    return render(request, 'attendance/session_edit.html', {
        'session': session,
        'activities': activities
    })


@login_required
def session_qr(request, pk):
    """Fullscreen QR display for projecting in a room."""
    session = get_object_or_404(
        AttendanceSession,
        pk=pk,
        status=AttendanceSession.SessionStatus.OPEN,
    )
    checkin_url = request.build_absolute_uri(f'/attendance/checkin/{session.qr_token}/')
    qr_data = _qr_base64(checkin_url)
    return render(request, 'attendance/qr_display.html', {
        'session': session,
        'qr_data': qr_data,
        'checkin_url': checkin_url,
        'now': timezone.now(),
    })


@login_required
def session_close(request, pk):
    """Close a session (no more check-ins)."""
    session = get_object_or_404(AttendanceSession, pk=pk)
    if request.user.role == 'STUDENT':
        messages.error(request, 'Bạn không có quyền đóng phiên điểm danh.')
        return redirect('attendance:session_detail', pk=pk)

    if request.method == 'POST':
        session.status = AttendanceSession.SessionStatus.CLOSED
        session.save()
        messages.success(request, f'Phiên "{session.name}" đã được đóng.')
    return redirect('attendance:session_detail', pk=pk)


# ────────────────────────────────────────────────────────────
# CHECK-IN (Student side – public URL via QR token)
# ────────────────────────────────────────────────────────────
def checkin_view(request, token):
    """Public check-in page opened via QR scan."""
    session = get_object_or_404(AttendanceSession, qr_token=token)

    if session.status != AttendanceSession.SessionStatus.OPEN:
        return render(request, 'attendance/checkin_closed.html', {'session': session})

    existing = None
    if request.user.is_authenticated:
        existing = AttendanceRecord.objects.filter(
            attendance_session=session,
            student=request.user,
        ).first()

    return render(request, 'attendance/checkin.html', {
        'session': session,
        'existing_record': existing,
        'now': timezone.now(),
    })


def checkin_submit(request, token):
    """Process student check-in submission (both authenticated and guests)."""
    session = get_object_or_404(AttendanceSession, qr_token=token)

    if session.status != AttendanceSession.SessionStatus.OPEN:
        messages.error(request, 'Phiên điểm danh đã đóng.')
        if request.user.is_authenticated:
            return redirect('attendance:sessions')
        return redirect('attendance:checkin', token=token)

    if request.method == 'POST':
        now = timezone.now()
        if now < session.start_time:
            messages.error(request, 'Chưa tới giờ điểm danh.')
            return redirect('attendance:checkin', token=token)
        if now > session.end_time:
            messages.error(request, 'Đã quá giờ điểm danh.')
            return redirect('attendance:checkin', token=token)

        student_instance = None
        student_code = None
        student_name = None

        if request.user.is_authenticated:
            student_instance = request.user
            student_code = getattr(student_instance, 'student_code', student_instance.username)
            student_name = student_instance.full_name
            # Prevent duplicate for authenticated users
            if AttendanceRecord.objects.filter(
                attendance_session=session, student=student_instance
            ).exists():
                messages.info(request, 'Bạn đã điểm danh trước đó rồi.')
                return redirect('attendance:checkin', token=token)
        else:
            student_code = request.POST.get('student_code', '').strip()
            student_name = request.POST.get('student_name', '').strip()

            if not student_code or not student_name:
                messages.error(request, 'Vui lòng nhập đầy đủ MSSV và Tên.')
                return redirect('attendance:checkin', token=token)

            # Prevent duplicate for guests based on student_code
            if AttendanceRecord.objects.filter(
                attendance_session=session, entered_student_code=student_code
            ).exists():
                messages.info(request, 'MSSV này đã được điểm danh trong phiên này rồi.')
                return redirect('attendance:checkin', token=token)

            # Attempt to link to an existing user if they have the same student_code
            from django.contrib.auth import get_user_model
            User = get_user_model()
            student_instance = User.objects.filter(
                Q(student_profile__student_code=student_code) | Q(username=student_code)
            ).first()

        # Determine status
        needs_photo = session.requires_photo
        record_status = 'PENDING' if needs_photo else 'VERIFIED'

        record = AttendanceRecord(
            attendance_session=session,
            student=student_instance,
            entered_student_code=student_code,
            entered_student_name=student_name,
            status=record_status,
        )

        # Handle optional photo
        if needs_photo and 'photo' in request.FILES:
            photo = request.FILES['photo']
            # Save manually since model uses photo_path (char field)
            from django.core.files.storage import default_storage
            path = default_storage.save(f'checkin/{session.pk}/{photo.name}', photo)
            record.photo_path = path

        record.save()

        if not needs_photo:
            if student_instance:
                _grant_points(student_instance, session.activity)
                messages.success(request, 'Điểm danh thành công! Điểm rèn luyện đã được ghi nhận.')
            else:
                messages.success(request, 'Điểm danh tư cách Khách thành công! (Cần liên kết tài khoản để nhận điểm).')
        else:
            messages.success(request, 'Đã nộp ảnh minh chứng! Chờ cán bộ xác nhận.')

    return redirect('attendance:checkin', token=token)


# ────────────────────────────────────────────────────────────
# RECORDS MANAGEMENT (Staff side)
# ────────────────────────────────────────────────────────────
@login_required
def records_list(request, session_pk):
    """List all records in a session for staff review."""
    session = get_object_or_404(AttendanceSession, pk=session_pk)
    if request.user.role == 'STUDENT':
        messages.error(request, 'Bạn không có quyền xem danh sách này.')
        return redirect('attendance:sessions')

    records = session.records.select_related('student', 'verified_by').order_by('status', '-checkin_time')
    
    pending_count = sum(1 for r in records if r.status == 'PENDING')
    
    return render(request, 'attendance/records_list.html', {
        'session': session,
        'records': records,
        'pending_count': pending_count,
    })

@login_required
def pending_sessions_view(request):
    """List all sessions that have pending attendance records."""
    if request.user.role == 'STUDENT':
        messages.error(request, 'Bạn không truy cập được.')
        return redirect('core:dashboard')

    sessions = AttendanceSession.objects.annotate(
        pending_count=Count('records', filter=Q(records__status='PENDING'))
    ).filter(
        pending_count__gt=0
    ).select_related('activity').order_by('-created_at')

    return render(request, 'attendance/pending_sessions.html', {'sessions': sessions})


@login_required
@transaction.atomic
def record_approve(request, pk):
    """Approve a PENDING record and grant points."""
    record = get_object_or_404(AttendanceRecord, pk=pk)
    if request.user.role == 'STUDENT':
        messages.error(request, 'Bạn không có quyền duyệt điểm danh.')
        return redirect('attendance:sessions')

    if request.method == 'POST' and record.status == 'PENDING':
        record.status = AttendanceRecord.RecordStatus.VERIFIED
        record.verified_by = request.user
        record.save()

        if record.student:
            _grant_points(record.student, record.activity)
            messages.success(request, f'Đã duyệt điểm danh cho {record.student.full_name}.')

    return redirect('attendance:records_list', session_pk=record.attendance_session_id)


@login_required
def record_reject(request, pk):
    """Reject a PENDING record."""
    record = get_object_or_404(AttendanceRecord, pk=pk)
    if request.user.role == 'STUDENT':
        messages.error(request, 'Bạn không có quyền từ chối điểm danh.')
        return redirect('attendance:sessions')

    if request.method == 'POST' and record.status == 'PENDING':
        record.status = AttendanceRecord.RecordStatus.REJECTED
        record.save()
        messages.success(request, 'Đã từ chối bản ghi điểm danh.')

    return redirect('attendance:records_list', session_pk=record.attendance_session_id)


# ────────────────────────────────────────────────────────────
# POINTS VIEW
# ────────────────────────────────────────────────────────────
@login_required
def points_view(request):
    """Display activity points."""
    if request.user.role == 'STUDENT':
        pts = ActivityPoint.objects.filter(
            student=request.user
        ).select_related('activity').order_by('-created_at')
    else:
        pts = ActivityPoint.objects.select_related(
            'student', 'activity'
        ).order_by('-created_at')

    total = sum(p.points for p in pts)
    return render(request, 'attendance/points.html', {
        'points': pts,
        'total_points': total,
    })


# ────────────────────────────────────────────────────────────
# PHASE 3: Verify attendance grouped by student × activity
# ────────────────────────────────────────────────────────────
@login_required
def activity_attendance_verify(request, activity_pk):
    """
    Staff/Admin view: attendance matrix for a single activity.
    Rows = Students who registered or checked in.
    Cols = AttendanceSessions (Phiên 1, Phiên 2, ...).
    Each cell: True/False (đã điểm danh phiên đó chưa).
    Shows total checked/total sessions and Award button per student.
    """
    if request.user.role == 'STUDENT':
        messages.error(request, 'Bạn không có quyền duyệt điểm danh.')
        return redirect('activities:detail', pk=activity_pk)

    activity = get_object_or_404(
        Activity.objects.select_related('point_category'),
        pk=activity_pk,
    )

    # All sessions for this activity (ordered)
    sessions = list(
        AttendanceSession.objects.filter(activity=activity).order_by('start_time')
    )

    # All records across all sessions of this activity
    all_records = AttendanceRecord.objects.filter(
        attendance_session__activity=activity,
        student__isnull=False,
    ).select_related('student', 'attendance_session')

    # Map student_id → student object
    student_map = {}
    # Map (student_id, session_id) → record
    record_map = {}
    for rec in all_records:
        sid = rec.student_id
        if sid not in student_map:
            student_map[sid] = rec.student
        record_map[(sid, rec.attendance_session_id)] = rec

    # Also include students who registered but haven't checked in yet
    from activities.models import ActivityRegistration
    registered = ActivityRegistration.objects.filter(
        activity=activity,
        status__in=['REGISTERED', 'ATTENDED', 'POINT_AWARDED'],
    ).select_related('student')
    for reg in registered:
        if reg.student_id not in student_map:
            student_map[reg.student_id] = reg.student

    # Build matrix rows
    total_sessions = len(sessions)

    # Students who already received points
    awarded_student_ids = set(
        ActivityPoint.objects.filter(activity=activity).values_list('student_id', flat=True)
    )

    student_rows = []
    for student_id, student in sorted(student_map.items(), key=lambda x: x[1].full_name):
        session_cells = []
        checked_count = 0
        for session in sessions:
            rec = record_map.get((student_id, session.pk))
            is_checked = rec is not None and rec.status in ('PENDING', 'VERIFIED')
            is_verified = rec is not None and rec.status == 'VERIFIED'
            session_cells.append({
                'session': session,
                'record': rec,
                'is_checked': is_checked,
                'is_verified': is_verified,
            })
            if is_checked:
                checked_count += 1

        is_fully_attended = (checked_count == total_sessions and total_sessions > 0)
        already_awarded = student_id in awarded_student_ids

        student_rows.append({
            'student': student,
            'cells': session_cells,
            'checked_count': checked_count,
            'total_sessions': total_sessions,
            'is_fully_attended': is_fully_attended,
            'already_awarded': already_awarded,
        })

    context = {
        'activity': activity,
        'sessions': sessions,
        'student_rows': student_rows,
        'total_students': len(student_rows),
        'fully_attended_count': sum(1 for r in student_rows if r['is_fully_attended']),
        'awarded_count': sum(1 for r in student_rows if r['already_awarded']),
        'active_tab': 'verify',
    }
    return render(request, 'attendance/activity_verify.html', context)


# ────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────
def _grant_points(student, activity, awarded_by=None):
    """Grant activity points (taken from activity.points), skip if already granted."""
    from django.utils import timezone as tz
    ActivityPoint.objects.get_or_create(
        student=student,
        activity=activity,
        defaults={
            'points': activity.points,
            'point_category': activity.point_category,
            'reason': 'ATTENDANCE',
            'awarded_by': awarded_by,
            'awarded_at': tz.now(),
        },
    )


# ────────────────────────────────────────────────────────────
# PHASE 4: Award Points — Individual + Bulk
# ────────────────────────────────────────────────────────────

def _do_award_student(student, activity, awarded_by):
    """
    Core award logic for a single student:
    1. Verify all PENDING attendance records for this student in the activity
    2. Create ActivityPoint (skips if already exists via unique constraint)
    3. Update ActivityRegistration → POINT_AWARDED
    Returns (awarded: bool, reason: str)
    """
    from activities.models import ActivityRegistration
    from django.utils import timezone as tz

    # 1. Mark all PENDING records as VERIFIED
    records_updated = AttendanceRecord.objects.filter(
        attendance_session__activity=activity,
        student=student,
        status=AttendanceRecord.RecordStatus.PENDING,
    ).update(
        status=AttendanceRecord.RecordStatus.VERIFIED,
        verified_by=awarded_by,
        approved_at=tz.now(),
    )

    # 2. Create ActivityPoint — skip if already exists
    _, created = ActivityPoint.objects.get_or_create(
        student=student,
        activity=activity,
        defaults={
            'points': activity.points,
            'point_category': activity.point_category,
            'reason': f'Hoàn thành hoạt động: {activity.title}',
            'awarded_by': awarded_by,
            'awarded_at': tz.now(),
        },
    )

    # 3. Update ActivityRegistration status
    ActivityRegistration.objects.filter(
        activity=activity,
        student=student,
        status__in=['REGISTERED', 'ATTENDED'],
    ).update(status='POINT_AWARDED')

    return created, records_updated


@login_required
@transaction.atomic
def award_student_points(request, activity_pk, student_pk):
    """
    Phase 4: Award points to a single student.
    POST only. Updates attendance records + creates ActivityPoint.
    Idempotent — calling again for same student is safe (skipped).
    """
    if request.user.role == 'STUDENT':
        messages.error(request, 'Bạn không có quyền cấp điểm.')
        return redirect('activities:detail', pk=activity_pk)

    if request.method != 'POST':
        return redirect('attendance:activity_verify', activity_pk=activity_pk)

    activity = get_object_or_404(
        Activity.objects.select_related('point_category'),
        pk=activity_pk,
    )

    from django.contrib.auth import get_user_model
    User = get_user_model()
    student = get_object_or_404(User, pk=student_pk)

    awarded, records_updated = _do_award_student(student, activity, awarded_by=request.user)

    if awarded:
        messages.success(
            request,
            f'✅ Đã cấp {activity.points} điểm rèn luyện cho {student.full_name}.'
            + (f' Xác nhận {records_updated} bản ghi điểm danh.' if records_updated else '')
        )
    else:
        messages.warning(
            request,
            f'{student.full_name} đã được cấp điểm trước đó — bỏ qua.'
        )

    return redirect('attendance:activity_verify', activity_pk=activity_pk)


@login_required
@transaction.atomic
def award_bulk_points(request, activity_pk):
    """
    Phase 4: Award points to multiple students at once.
    POST only.
    - If eligible_only=1: only award students with all sessions checked
    - Otherwise: award all students not yet awarded
    Returns summary of awarded / skipped counts.
    """
    if request.user.role == 'STUDENT':
        messages.error(request, 'Bạn không có quyền cấp điểm.')
        return redirect('activities:detail', pk=activity_pk)

    if request.method != 'POST':
        return redirect('attendance:activity_verify', activity_pk=activity_pk)

    activity = get_object_or_404(
        Activity.objects.select_related('point_category'),
        pk=activity_pk,
    )

    eligible_only = request.POST.get('eligible_only') == '1'

    # Get all sessions count
    sessions = AttendanceSession.objects.filter(activity=activity)
    total_sessions = sessions.count()

    # Already awarded student IDs
    awarded_ids = set(
        ActivityPoint.objects.filter(activity=activity).values_list('student_id', flat=True)
    )

    # Candidates: students who checked in to at least 1 session
    from django.contrib.auth import get_user_model
    from django.db.models import Count
    User = get_user_model()

    candidate_qs = User.objects.filter(
        attendance_records__attendance_session__activity=activity,
        attendance_records__status__in=['PENDING', 'VERIFIED'],
    ).annotate(
        checked_sessions=Count('attendance_records__attendance_session', distinct=True)
    ).distinct()

    awarded_count = 0
    skipped_count = 0

    for student in candidate_qs:
        # Skip already-awarded
        if student.pk in awarded_ids:
            skipped_count += 1
            continue

        # Filter by eligible_only
        if eligible_only and total_sessions > 0:
            if student.checked_sessions < total_sessions:
                skipped_count += 1
                continue

        _, was_awarded = _do_award_student(student, activity, awarded_by=request.user)
        if was_awarded:
            awarded_count += 1
        else:
            skipped_count += 1

    if awarded_count > 0:
        messages.success(
            request,
            f'✅ Đã cấp điểm cho {awarded_count} sinh viên.'
            + (f' Bỏ qua {skipped_count} (đã cấp hoặc chưa đủ điều kiện).' if skipped_count else '')
        )
    else:
        messages.warning(request, 'Không có sinh viên nào được cấp điểm mới.')

    return redirect('attendance:activity_verify', activity_pk=activity_pk)
