import base64
import io
import uuid

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from activities.models import Activity, ActivityParticipation
from django.db.models import Count, Q
from .models import AttendanceSession


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
def activity_sessions_list(request, activity_pk):
    """List attendance sessions scoped to a specific activity."""
    activity = get_object_or_404(Activity, pk=activity_pk)
    qs = AttendanceSession.objects.filter(activity=activity).order_by('-created_at')
    
    # Students see only open sessions if they are registered
    if request.user.role == 'STUDENT':
        is_registered = request.user.activity_participations.filter(activity=activity).exists()
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
    records = session.participations.select_related('student', 'verified_by').order_by('-checkin_time')
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
        return redirect('activities:list')

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
        existing = ActivityParticipation.objects.filter(
            attendance_session=session,
            student=request.user,
        ).first()
    else:
        # Check guest session cookie
        guest_record_id = request.session.get(f'guest_record_{token}')
        if guest_record_id:
            existing = ActivityParticipation.objects.filter(
                id=guest_record_id,
                attendance_session=session
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
            return redirect('activities:list')
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
            if ActivityParticipation.objects.filter(
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

            # Prevent duplicate for guests based on student_code AND student_name
            if ActivityParticipation.objects.filter(
                attendance_session=session,
                entered_student_code__iexact=student_code,
                entered_student_name__iexact=student_name
            ).exists():
                messages.info(request, 'Bạn đã điểm danh trong phiên này với tên và MSSV này rồi.')
                return redirect('attendance:checkin', token=token)

            # Do not link student_instance right now to avoid UniqueConstraint errors
            # if multiple guests use the same student_code. Linking will happen on verify.
            student_instance = None

        # Determine status and validate photo first
        needs_photo = session.requires_photo
        if needs_photo and 'photo' not in request.FILES:
            messages.error(request, 'Vui lòng cung cấp ảnh minh chứng.')
            return redirect('attendance:checkin', token=token)

        record_status = 'ATTENDED' if needs_photo else 'VERIFIED'

        if student_instance:
            record, _ = ActivityParticipation.objects.get_or_create(
                activity=session.activity,
                student=student_instance,
                defaults={
                    'entered_student_code': student_code,
                    'entered_student_name': student_name,
                }
            )
        else:
            record = ActivityParticipation.objects.create(
                activity=session.activity,
                student=None,
                entered_student_code=student_code,
                entered_student_name=student_name,
            )
            
        record.attendance_session = session
        record.status = record_status
        record.checkin_time = now


        # Handle optional photo
        if needs_photo and 'photo' in request.FILES:
            photo = request.FILES['photo']
            # Save manually since model uses photo_path (char field)
            from django.core.files.storage import default_storage
            path = default_storage.save(f'checkin/{session.pk}/{photo.name}', photo)
            record.photo_path = path

        record.save()

        # Save session for guests
        if not request.user.is_authenticated:
            request.session[f'guest_record_{session.qr_token}'] = record.pk

        if not needs_photo:
            if student_instance:
                awarded = _check_and_auto_award(student_instance, session.activity)
                if awarded:
                    messages.success(request, 'Điểm danh thành công! Đã đủ số phiên và được cấp điểm rèn luyện.')
                else:
                    messages.success(request, 'Điểm danh thành công!')
            else:
                messages.success(request, 'Điểm danh tư cách Khách thành công! (Cần liên kết tài khoản để nhận điểm).')
        else:
            messages.success(request, 'Đã nộp ảnh minh chứng! Chờ cán bộ xác nhận.')

    return redirect('attendance:checkin', token=token)


def checkin_guest_reset(request, token):
    """Reset guest checkin status by deleting the record if it is still ATTENDED."""
    if request.method == 'POST':
        guest_record_id = request.session.get(f'guest_record_{token}')
        if guest_record_id:
            record = ActivityParticipation.objects.filter(id=guest_record_id).first()
            if record and record.status == 'ATTENDED':
                record.delete()
                
            if f'guest_record_{token}' in request.session:
                del request.session[f'guest_record_{token}']
                
        messages.success(request, 'Đã hủy thông tin điểm danh cũ, bạn có thể nhập lại.')
    return redirect('attendance:checkin', token=token)


def checkin_reupload_photo(request, token):
    """Reupload photo for an existing ATTENDED or REJECTED record."""
    if request.method == 'POST' and 'photo' in request.FILES:
        session = get_object_or_404(AttendanceSession, qr_token=token)
        existing_record = None
        
        if request.user.is_authenticated:
            existing_record = ActivityParticipation.objects.filter(
                attendance_session=session,
                student=request.user,
            ).first()
        else:
            guest_record_id = request.session.get(f'guest_record_{token}')
            if guest_record_id:
                existing_record = ActivityParticipation.objects.filter(
                    id=guest_record_id,
                    attendance_session=session
                ).first()

        if existing_record and existing_record.status in ['ATTENDED', 'ABSENT']:
            photo = request.FILES['photo']
            from django.core.files.storage import default_storage
            
            if existing_record.photo_path and default_storage.exists(existing_record.photo_path):
                default_storage.delete(existing_record.photo_path)
            
            path = default_storage.save(f'checkin/{session.pk}/{photo.name}', photo)
            existing_record.photo_path = path
            existing_record.status = 'ATTENDED'  # Move back to pending
            existing_record.save()
            messages.success(request, 'Đã nộp ảnh minh chứng mới thành công! Chờ cán bộ xác nhận.')

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
        return redirect('activities:list')

    records = session.participations.select_related('student', 'verified_by').order_by('status', 'entered_student_code', '-checkin_time')
    
    pending_count = sum(1 for r in records if r.status == 'ATTENDED')
    
    # Identify duplicates 
    from collections import Counter
    pending_mssvs = [r.entered_student_code.upper() for r in records if r.status == 'ATTENDED' and r.entered_student_code]
    duplicate_mssvs = {mssv for mssv, count in Counter(pending_mssvs).items() if count > 1}
    
    for r in records:
        r.is_duplicate_conflict = (r.status == 'ATTENDED' and r.entered_student_code and r.entered_student_code.upper() in duplicate_mssvs)
    
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
        pending_count=Count('records', filter=Q(records__status='ATTENDED'))
    ).filter(
        pending_count__gt=0
    ).select_related('activity').order_by('-created_at')

    return render(request, 'attendance/pending_sessions.html', {'sessions': sessions})


@login_required
@transaction.atomic
def record_approve(request, pk):
    """Approve a PENDING record and grant points."""
    record = get_object_or_404(ActivityParticipation, pk=pk)
    if request.user.role == 'STUDENT':
        messages.error(request, 'Bạn không có quyền duyệt điểm danh.')
        return redirect('activities:list')

    if request.method == 'POST' and record.status == 'ATTENDED':
        # Try to link student if null
        if not record.student and record.entered_student_code:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            student_instance = User.objects.filter(
                Q(student_profile__student_code=record.entered_student_code) | Q(username=record.entered_student_code)
            ).first()
            if student_instance:
                if not ActivityParticipation.objects.filter(activity=record.activity, student=student_instance).exclude(pk=record.pk).exists():
                    record.student = student_instance

        record.status = 'VERIFIED'
        record.verified_by = request.user
        record.save()

        # Reject duplicates
        if record.entered_student_code:
            ActivityParticipation.objects.filter(
                attendance_session=record.attendance_session,
                entered_student_code__iexact=record.entered_student_code,
                status='ATTENDED'
            ).exclude(pk=record.pk).update(status='ABSENT')

        if record.student:
            awarded = _check_and_auto_award(record.student, record.activity, awarded_by=request.user)
            if awarded:
                messages.success(request, f'Đã duyệt điểm danh cho {record.student.full_name} và cấp điểm rèn luyện.')
            else:
                messages.success(request, f'Đã duyệt điểm danh cho {record.student.full_name}.')
        else:
            messages.success(request, 'Đã duyệt điểm danh cho khách.')

    return redirect('attendance:records_list', session_pk=record.attendance_session_id or record.attendance_session.pk)


@login_required
def record_reject(request, pk):
    """Reject a PENDING record."""
    record = get_object_or_404(ActivityParticipation, pk=pk)
    if request.user.role == 'STUDENT':
        messages.error(request, 'Bạn không có quyền từ chối điểm danh.')
        return redirect('activities:list')

    if request.method == 'POST' and record.status == 'ATTENDED':
        record.status = 'ABSENT'
        record.save()
        messages.success(request, 'Đã từ chối bản ghi điểm danh.')

    return redirect('attendance:records_list', session_pk=record.attendance_session_id or record.attendance_session.pk)


@login_required
@transaction.atomic
def records_bulk_approve(request, session_pk):
    """Approve all PENDING records in a specific session."""
    session = get_object_or_404(AttendanceSession, pk=session_pk)
    if request.user.role == 'STUDENT':
        messages.error(request, 'Bạn không có quyền duyệt điểm danh.')
        return redirect('activities:list')

    if request.method == 'POST':
        pending_records = session.participations.filter(status='ATTENDED').select_related('student')
        count = 0
        from django.utils import timezone as tz
        now = tz.now()

        for record in pending_records:
            record.status = 'VERIFIED'
            record.verified_by = request.user
            record.approved_at = now
            record.save()
            count += 1

            if record.student:
                _check_and_auto_award(record.student, session.activity, awarded_by=request.user)

        if count > 0:
            messages.success(request, f'Đã duyệt thành công {count} bản ghi chờ xác nhận.')
        else:
            messages.warning(request, 'Không có bản ghi nào đang chờ xác nhận.')

    return redirect('attendance:records_list', session_pk=session_pk)

# ────────────────────────────────────────────────────────────
# POINTS VIEW
# ────────────────────────────────────────────────────────────
@login_required
def points_view(request):
    """Display activity points."""
    if request.user.role == 'STUDENT':
        pts = ActivityParticipation.objects.filter(
            student=request.user, awarded_points__gt=0
        ).select_related('activity').order_by('-awarded_at')
    else:
        pts = ActivityParticipation.objects.filter(awarded_points__gt=0).select_related(
            'student', 'activity'
        ).order_by('-awarded_at')

    total = sum(p.awarded_points for p in pts)
    return render(request, 'attendance/points.html', {
        'points': pts,
        'total_points': total,
    })


# ────────────────────────────────────────────────────────────
# PHASE 3: Verify attendance & Points Map
# ────────────────────────────────────────────────────────────
@login_required
def activity_attendance_verify(request, activity_pk):
    if request.user.role == 'STUDENT':
        messages.error(request, 'Bạn không có quyền duyệt điểm danh.')
        return redirect('activities:detail', pk=activity_pk)

    activity = get_object_or_404(
        Activity.objects.select_related('point_category'),
        pk=activity_pk,
    )

    participations = ActivityParticipation.objects.filter(activity=activity).select_related('student', 'attendance_session')
    sessions = list(AttendanceSession.objects.filter(activity=activity).order_by('start_time'))

    student_rows = []
    awarded_count = 0
    fully_attended_count = 0

    for part in participations:
        student = part.student
        is_fully_attended = part.status == 'VERIFIED' or part.status == 'ATTENDED'
        already_awarded = part.awarded_points > 0

        if is_fully_attended: fully_attended_count += 1
        if already_awarded: awarded_count += 1

        cells = []
        for session in sessions:
            is_checked = part.attendance_session_id == session.id and part.status in ['ATTENDED', 'VERIFIED']
            cells.append({
                'session': session,
                'is_checked': is_checked,
                'is_verified': part.status == 'VERIFIED',
                'record': part if part.attendance_session_id == session.id else None
            })

        student_rows.append({
            'part': part,
            'student': student,
            'cells': cells,
            'checked_count': 1 if is_fully_attended else 0,
            'total_sessions': 1,
            'is_fully_attended': is_fully_attended,
            'already_awarded': already_awarded,
        })

    context = {
        'activity': activity,
        'sessions': sessions,
        'student_rows': student_rows,
        'total_students': len(student_rows),
        'fully_attended_count': fully_attended_count,
        'awarded_count': awarded_count,
        'active_tab': 'verify',
    }
    return render(request, 'attendance/activity_verify.html', context)


def _check_and_auto_award(student, activity, awarded_by=None):
    from django.utils import timezone as tz
    part = ActivityParticipation.objects.filter(student=student, activity=activity).first()
    if part and part.status == 'VERIFIED':
        if part.awarded_points == 0:
            part.awarded_points = activity.points
            part.point_category = activity.point_category
            part.awarded_by = awarded_by
            part.awarded_at = tz.now()
            part.save()
            return True
    return False

def _do_award_student(student, activity, awarded_by):
    from django.utils import timezone as tz
    part = ActivityParticipation.objects.filter(student=student, activity=activity).first()
    if part and part.awarded_points == 0:
        if part.status == 'ATTENDED':
            part.status = 'VERIFIED'
        part.awarded_points = activity.points
        part.point_category = activity.point_category
        part.awarded_by = awarded_by
        part.awarded_at = tz.now()
        part.save()
        return True, 1
    return False, 0

@login_required
@transaction.atomic
def award_student_points(request, activity_pk, student_pk):
    if request.user.role == 'STUDENT':
        return redirect('activities:detail', pk=activity_pk)

    activity = get_object_or_404(Activity, pk=activity_pk)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    student = get_object_or_404(User, pk=student_pk)

    awarded, recs = _do_award_student(student, activity, request.user)
    if awarded: messages.success(request, f'Đã cấp điểm cho {student.full_name}.')
    return redirect('attendance:activity_verify', activity_pk=activity_pk)


@login_required
@transaction.atomic
def award_revoke_student_points(request, activity_pk, student_pk):
    if request.user.role == 'STUDENT':
        return redirect('activities:detail', pk=activity_pk)
    
    activity = get_object_or_404(Activity, pk=activity_pk)
    from django.contrib.auth import get_user_model
    student = get_object_or_404(get_user_model(), pk=student_pk)

    part = ActivityParticipation.objects.filter(student=student, activity=activity).first()
    if part:
        part.awarded_points = 0
        part.point_category = None
        part.awarded_by = None
        part.awarded_at = None
        part.save()
        messages.success(request, f'Đã hủy điểm của {student.full_name}.')
    return redirect('attendance:activity_verify', activity_pk=activity_pk)


@login_required
@transaction.atomic
def award_bulk_points(request, activity_pk):
    if request.user.role == 'STUDENT': return redirect('activities:detail', pk=activity_pk)
    activity = get_object_or_404(Activity, pk=activity_pk)

    parts = ActivityParticipation.objects.filter(activity=activity, status__in=['VERIFIED', 'ATTENDED'], awarded_points=0)
    count = 0
    from django.utils import timezone as tz
    now = tz.now()
    for part in parts:
        part.status = 'VERIFIED'
        part.awarded_points = activity.points
        part.point_category = activity.point_category
        part.awarded_by = request.user
        part.awarded_at = now
        part.save()
        count += 1
    messages.success(request, f'Đã cấp điểm cho {count} sinh viên.')
    return redirect('attendance:activity_verify', activity_pk=activity_pk)
