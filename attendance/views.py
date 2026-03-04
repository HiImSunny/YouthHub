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

    context = {'sessions': qs.order_by('-created_at')}
    return render(request, 'attendance/sessions.html', context)


@login_required
def session_create(request):
    """Create a new attendance session (STAFF/ADMIN only)."""
    if request.user.role == 'STUDENT':
        messages.error(request, 'Ban khong co quyen tao phien diem danh.')
        return redirect('attendance:sessions')

    if request.method == 'POST':
        activity_id = request.POST.get('activity')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')

        session = AttendanceSession(
            activity_id=activity_id,
            name=request.POST.get('name'),
            start_time=start_time,
            end_time=end_time,
            requires_photo=request.POST.get('requires_photo') == 'on',
            qr_token=uuid.uuid4().hex,
            status=AttendanceSession.SessionStatus.OPEN,
        )
        session.save()
        messages.success(request, f'Phien diem danh "{session.name}" da duoc tao!')
        return redirect('attendance:session_detail', pk=session.pk)

    activities = Activity.objects.filter(status__in=['APPROVED', 'ONGOING']).order_by('-start_time')
    return render(request, 'attendance/session_form.html', {'activities': activities})


@login_required
def session_detail(request, pk):
    """View session details and its records."""
    session = get_object_or_404(
        AttendanceSession.objects.select_related('activity'),
        pk=pk,
    )
    records = session.records.select_related('student', 'verified_by').order_by('-checkin_time')
    checkin_url = request.build_absolute_uri(f'/attendance/checkin/{session.qr_token}/')

    context = {
        'session': session,
        'records': records,
        'checkin_url': checkin_url,
        'approved_count': records.filter(status='VERIFIED').count(),
        'pending_count': records.filter(status='PENDING').count(),
        'rejected_count': records.filter(status='REJECTED').count(),
    }
    return render(request, 'attendance/session_detail.html', context)


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
    })


@login_required
def session_close(request, pk):
    """Close a session (no more check-ins)."""
    session = get_object_or_404(AttendanceSession, pk=pk)
    if request.user.role == 'STUDENT':
        messages.error(request, 'Ban khong co quyen dong phien diem danh.')
        return redirect('attendance:session_detail', pk=pk)

    if request.method == 'POST':
        session.status = AttendanceSession.SessionStatus.CLOSED
        session.save()
        messages.success(request, f'Phien "{session.name}" da duoc dong.')
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
    })


@login_required
def checkin_submit(request, token):
    """Process student check-in submission."""
    session = get_object_or_404(AttendanceSession, qr_token=token)

    if session.status != AttendanceSession.SessionStatus.OPEN:
        messages.error(request, 'Phien diem danh da dong.')
        return redirect('attendance:sessions')

    if request.method == 'POST':
        # Prevent duplicate
        if AttendanceRecord.objects.filter(
            attendance_session=session, student=request.user
        ).exists():
            messages.info(request, 'Ban da diem danh truoc do roi.')
            return redirect('attendance:checkin', token=token)

        # Determine status
        needs_photo = session.requires_photo
        record_status = 'PENDING' if needs_photo else 'VERIFIED'

        record = AttendanceRecord(
            attendance_session=session,
            student=request.user,
            entered_student_code=getattr(request.user, 'student_code', request.user.username),
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
            _grant_points(request.user, session.activity)
            messages.success(request, 'Diem danh thanh cong! Diem ren luyen da duoc ghi nhan.')
        else:
            messages.success(request, 'Da nop anh minh chung! Cho can bo xac nhan.')

    return redirect('attendance:checkin', token=token)


# ────────────────────────────────────────────────────────────
# RECORDS MANAGEMENT (Staff side)
# ────────────────────────────────────────────────────────────
@login_required
def records_list(request, session_pk):
    """List all records in a session for staff review."""
    session = get_object_or_404(AttendanceSession, pk=session_pk)
    if request.user.role == 'STUDENT':
        messages.error(request, 'Ban khong co quyen xem danh sach nay.')
        return redirect('attendance:sessions')

    records = session.records.select_related('student', 'verified_by').order_by('status', '-checkin_time')
    return render(request, 'attendance/records_list.html', {
        'session': session,
        'records': records,
    })


@login_required
@transaction.atomic
def record_approve(request, pk):
    """Approve a PENDING record and grant points."""
    record = get_object_or_404(AttendanceRecord, pk=pk)
    if request.user.role == 'STUDENT':
        messages.error(request, 'Ban khong co quyen duyet diem danh.')
        return redirect('attendance:sessions')

    if request.method == 'POST' and record.status == 'PENDING':
        record.status = AttendanceRecord.RecordStatus.VERIFIED
        record.verified_by = request.user
        record.save()

        if record.student:
            _grant_points(record.student, record.activity)
            messages.success(request, f'Da duyet diem danh cho {record.student.full_name}.')

    return redirect('attendance:records_list', session_pk=record.attendance_session_id)


@login_required
def record_reject(request, pk):
    """Reject a PENDING record."""
    record = get_object_or_404(AttendanceRecord, pk=pk)
    if request.user.role == 'STUDENT':
        messages.error(request, 'Ban khong co quyen tu choi diem danh.')
        return redirect('attendance:sessions')

    if request.method == 'POST' and record.status == 'PENDING':
        record.status = AttendanceRecord.RecordStatus.REJECTED
        record.save()
        messages.success(request, 'Da tu choi bản ghi diem danh.')

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
