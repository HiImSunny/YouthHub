"""
Celery tasks for attendance app.
Handles high-concurrency check-in processing asynchronously.

Architecture:
  - checkin_submit view validates quickly (fast path) then fires Celery task
  - process_checkin task writes to DB, handles photo, awards points
  - Redis cache stores session info to avoid 1000 identical DB queries
"""
import logging
import os

from celery import shared_task
from django.core.cache import cache
from django.db import transaction

logger = logging.getLogger(__name__)

# Cache TTL constants
SESSION_CACHE_TTL = 300   # 5 min: session info cached (token -> session pk, status, times)
CHECKIN_LOCK_TTL = 10     # 10 sec: per-user distributed lock to prevent double-submit


def _get_session_cache_key(token: str) -> str:
    return f"attendance_session:{token}"


def _get_checkin_lock_key(token: str, identifier: str) -> str:
    """identifier is user pk (authenticated) or student_code (guest)."""
    return f"checkin_lock:{token}:{identifier}"


def get_cached_session_info(token: str):
    """
    Return lightweight dict of session info from Redis cache.
    Avoids repeated DB hits when 1000+ users scan the same QR simultaneously.

    Returns dict with keys: pk, status, start_time, end_time, requires_photo
    Returns None if not in cache.
    """
    return cache.get(_get_session_cache_key(token))


def set_cached_session_info(session):
    """Populate Redis cache with session data after a DB hit."""
    data = {
        'pk': session.pk,
        'status': session.status,
        'start_time': session.start_time.isoformat(),
        'end_time': session.end_time.isoformat(),
        'requires_photo': session.requires_photo,
        'activity_pk': session.activity_id,
    }
    cache.set(_get_session_cache_key(session.qr_token), data, SESSION_CACHE_TTL)
    return data


def invalidate_session_cache(token: str):
    """Bust cache when session status changes (e.g. closed)."""
    cache.delete(_get_session_cache_key(token))


def try_acquire_checkin_lock(token: str, identifier: str) -> bool:
    """
    Distributed lock via Redis to prevent race-condition double-submit.
    Returns True if lock acquired, False if already locked (duplicate request).
    """
    lock_key = _get_checkin_lock_key(token, identifier)
    # nx=True: only set if not exists → atomic check-and-set
    return cache.add(lock_key, 1, CHECKIN_LOCK_TTL)


def release_checkin_lock(token: str, identifier: str):
    cache.delete(_get_checkin_lock_key(token, identifier))


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ASYNC CHECK-IN TASK
# ─────────────────────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    name='attendance.tasks.process_checkin',
    max_retries=3,
    default_retry_delay=5,
    time_limit=60,
    soft_time_limit=50,
    queue='checkin',
)
def process_checkin(
    self,
    session_pk: int,
    student_pk,          # int or None (guests)
    student_code: str,
    student_name: str,
    photo_bytes_b64,     # base64-encoded string or None
    photo_name: str,
    checkin_time_iso: str,
    qr_token: str,
):
    """
    Async Celery task that writes the check-in record to the database.

    Offloads all DB writes and file I/O from the request/response cycle so
    HTTP workers can return < 100ms to the browser even under 1000+ concurrent
    check-ins.

    Args:
        session_pk: AttendanceSession PK
        student_pk: authenticated User PK (None for guests)
        student_code: MSSV entered by user
        student_name: Full name entered by user
        photo_bytes_b64: base64-encoded photo bytes (None if no photo)
        photo_name: original filename for storage path
        checkin_time_iso: ISO datetime string of when user submitted
        qr_token: session QR token (used to release Redis lock on error)
    """
    from django.utils.dateparse import parse_datetime
    from django.utils import timezone
    from activities.models import ActivityParticipation
    from attendance.models import AttendanceSession

    try:
        with transaction.atomic():
            session = AttendanceSession.objects.select_related('activity').get(pk=session_pk)

            # Re-check session status (might have closed between submit and task execution)
            if session.status != AttendanceSession.SessionStatus.OPEN:
                logger.info(f"[Checkin] Session #{session_pk} is no longer OPEN. Aborting task.")
                return {'status': 'aborted', 'reason': 'session_closed'}

            checkin_time = parse_datetime(checkin_time_iso)
            if checkin_time is None:
                checkin_time = timezone.now()

            needs_photo = session.requires_photo
            record_status = 'ATTENDED' if needs_photo else 'VERIFIED'

            student_instance = None
            if student_pk:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    student_instance = User.objects.get(pk=student_pk)
                except User.DoesNotExist:
                    pass

            # Create or update participation record
            if student_instance:
                record, created = ActivityParticipation.objects.get_or_create(
                    activity=session.activity,
                    student=student_instance,
                    defaults={
                        'entered_student_code': student_code,
                        'entered_student_name': student_name,
                    }
                )
                if not created:
                    # Already registered — just update check-in fields
                    if record.status in ('REGISTERED', 'CANCELED'):
                        record.entered_student_code = student_code
                        record.entered_student_name = student_name
                    else:
                        # Already checked in or verified — skip silently
                        logger.info(f"[Checkin] Student #{student_pk} already checked in for session #{session_pk}.")
                        return {'status': 'duplicate', 'record_pk': record.pk}
            else:
                # Guest: always create new record
                record = ActivityParticipation(
                    activity=session.activity,
                    student=None,
                    entered_student_code=student_code,
                    entered_student_name=student_name,
                )

            record.attendance_session = session
            record.status = record_status
            record.checkin_time = checkin_time

            # Handle photo upload (now done in background — no request blocking)
            if needs_photo and photo_bytes_b64:
                import base64
                from django.core.files.storage import default_storage
                from django.core.files.base import ContentFile

                photo_bytes = base64.b64decode(photo_bytes_b64)
                save_path = f"checkin/{session.pk}/{photo_name}"
                path = default_storage.save(save_path, ContentFile(photo_bytes))
                record.photo_path = path
                logger.info(f"[Checkin] Photo saved: {path}")

            record.save()

            # Auto award points for no-photo (instant verified) check-ins
            if not needs_photo and student_instance:
                _award_if_eligible(student_instance, session.activity)

        logger.info(
            f"[Checkin] Task done: student={student_pk or student_code!r}, "
            f"session={session_pk}, status={record_status}, record={record.pk}"
        )
        return {'status': 'ok', 'record_pk': record.pk, 'record_status': record_status}

    except Exception as exc:
        logger.error(f"[Checkin] Task failed for session #{session_pk}: {exc}", exc_info=True)
        # Release Redis lock so the student can retry
        identifier = str(student_pk) if student_pk else student_code
        release_checkin_lock(qr_token, identifier)
        raise self.retry(exc=exc)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _award_if_eligible(student, activity, awarded_by=None):
    """Auto-award training points when participation is instantly VERIFIED."""
    from activities.models import ActivityParticipation
    from django.utils import timezone as tz

    try:
        part = ActivityParticipation.objects.filter(student=student, activity=activity).first()
        if part and part.status == 'VERIFIED' and part.awarded_points == 0:
            part.awarded_points = activity.points
            part.point_category = activity.point_category
            part.awarded_by = awarded_by
            part.awarded_at = tz.now()
            part.save(update_fields=['awarded_points', 'point_category', 'awarded_by', 'awarded_at'])
            logger.info(f"[Checkin] Auto-awarded {activity.points} pts to {student}")
    except Exception as e:
        logger.warning(f"[Checkin] Auto-award failed: {e}")
