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
    student_pk,
    student_code: str,
    student_name: str,
    photo_bytes_b64,
    photo_name: str,
    checkin_time_iso: str,
    qr_token: str,
):
    """
    Async Celery task that writes the check-in record to the database.

    Design pattern (fixes Windows eventlet file I/O crash):
    1. Save DB record inside transaction (fast, no file I/O).
    2. Save photo file AFTER transaction commits — file failure won't
       roll back the record, ensuring email signals can always find it.
    3. All Redis cache operations wrapped in try/except (best-effort).
    """
    from django.utils.dateparse import parse_datetime
    from django.utils import timezone
    from activities.models import ActivityParticipation
    from attendance.models import AttendanceSession

    identifier = str(student_pk) if student_pk else student_code
    record = None

    try:
        session = AttendanceSession.objects.select_related('activity').get(pk=session_pk)

        if session.status != AttendanceSession.SessionStatus.OPEN:
            logger.info(f"[Checkin] Session #{session_pk} no longer OPEN. Aborting.")
            return {'status': 'aborted', 'reason': 'session_closed'}

        checkin_time = parse_datetime(checkin_time_iso) or timezone.now()
        needs_photo = session.requires_photo
        record_status = 'ATTENDED' if needs_photo else 'VERIFIED'

        student_instance = None
        if student_pk:
            from django.contrib.auth import get_user_model
            try:
                student_instance = get_user_model().objects.get(pk=student_pk)
            except Exception:
                pass

        # ── Step A: Commit DB record (transaction, NO file I/O) ─────────────
        with transaction.atomic():
            if student_instance:
                record, created = ActivityParticipation.objects.get_or_create(
                    activity=session.activity,
                    student=student_instance,
                    defaults={
                        'entered_student_code': student_code,
                        'entered_student_name': student_name,
                    }
                )
                if not created and record.status not in ('REGISTERED', 'CANCELED'):
                    logger.info(f"[Checkin] Duplicate — student #{student_pk}, session #{session_pk}.")
                    return {'status': 'duplicate', 'record_pk': record.pk}
            else:
                record = ActivityParticipation(
                    activity=session.activity,
                    student=None,
                    entered_student_code=student_code,
                    entered_student_name=student_name,
                )

            record.attendance_session = session
            record.status = record_status
            record.checkin_time = checkin_time
            # photo_path will be set below; save record first so signal fires with committed data
            record.save()

        # ── Step B: Save photo OUTSIDE transaction (file I/O won't rollback record) ──
        if needs_photo and photo_bytes_b64 and record:
            try:
                import base64 as _b64
                from django.core.files.storage import default_storage
                from django.core.files.base import ContentFile

                raw = _b64.b64decode(photo_bytes_b64)
                save_path = f"checkin/{session.pk}/{photo_name}"
                path = default_storage.save(save_path, ContentFile(raw))
                ActivityParticipation.objects.filter(pk=record.pk).update(photo_path=path)
                logger.info(f"[Checkin] Photo saved: {path}")
            except Exception as photo_err:
                logger.warning(
                    f"[Checkin] Photo save failed for record #{record.pk}: {photo_err}. "
                    f"Record stays ATTENDED — student can re-upload."
                )

        # ── Step C: Auto-award points if no photo required ───────────────────
        if not needs_photo and student_instance and record:
            _award_if_eligible(student_instance, session.activity)

        logger.info(
            f"[Checkin] OK: student={student_pk or student_code!r}, "
            f"session={session_pk}, status={record_status}, pk={record.pk}"
        )
        return {'status': 'ok', 'record_pk': record.pk, 'record_status': record_status}

    except Exception as exc:
        logger.error(f"[Checkin] Task failed (session #{session_pk}): {exc}", exc_info=True)
        # Best-effort lock release — wrapped so Redis errors don't mask real error
        try:
            release_checkin_lock(qr_token, identifier)
        except Exception as lock_err:
            logger.warning(f"[Checkin] Lock release failed: {lock_err}")
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
