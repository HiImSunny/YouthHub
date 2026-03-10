"""
Celery tasks for core app.
Handles async email notifications for activities and attendance.
"""
import logging

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# ACTIVITY REGISTRATION EMAIL
# ─────────────────────────────────────────

@shared_task(
    bind=True,
    name='core.send_activity_registration_email',
    max_retries=3,
    default_retry_delay=60,   # Retry after 60s if SMTP fails
    time_limit=30,
)
def send_activity_registration_email(self, participation_id: int):
    """
    Send confirmation email when a student registers for an activity.

    Args:
        participation_id: PK of ActivityParticipation record
    """
    try:
        from activities.models import ActivityParticipation
        participation = ActivityParticipation.objects.select_related(
            'activity', 'student'
        ).get(pk=participation_id)

        student = participation.student
        activity = participation.activity

        # Only send if student has email
        if not student or not getattr(student, 'email', None):
            logger.info(f"[Celery] Skipping email for participation #{participation_id}: no email")
            return {'status': 'skipped', 'reason': 'no_email'}

        subject = f'[YouthHub] Xac nhan dang ky: {activity.title}'

        # Try HTML template, fallback to plain text
        try:
            html_message = render_to_string('emails/registration_confirm.html', {
                'student': student,
                'activity': activity,
                'participation': participation,
            })
        except Exception:
            html_message = None

        plain_message = (
            f'Xin chao {student.get_full_name() or student.username},\n\n'
            f'Ban da dang ky tham gia hoat dong: {activity.title}\n'
            f'Thoi gian: {activity.start_date}\n'
            f'Don vi to chuc: {activity.organization}\n\n'
            f'Cam on ban da tham gia!\n'
            f'-- YouthHub Team'
        )

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"[Celery] Registration email sent to {student.email} for activity #{activity.pk}")
        return {'status': 'sent', 'email': student.email, 'activity_id': activity.pk}

    except Exception as exc:
        logger.warning(f"[Celery] Email task failed for participation #{participation_id}: {exc}")
        # Retry automatically (up to max_retries)
        raise self.retry(exc=exc)


# ─────────────────────────────────────────
# ATTENDANCE VERIFIED EMAIL
# ─────────────────────────────────────────

@shared_task(
    bind=True,
    name='core.send_attendance_verified_email',
    max_retries=3,
    default_retry_delay=60,
    time_limit=30,
)
def send_attendance_verified_email(self, participation_id: int):
    """
    Send confirmation email when a student's attendance is verified/approved.

    Args:
        participation_id: PK of ActivityParticipation record
    """
    try:
        from activities.models import ActivityParticipation
        participation = ActivityParticipation.objects.select_related(
            'activity', 'student'
        ).get(pk=participation_id)

        student = participation.student
        activity = participation.activity

        if not student or not getattr(student, 'email', None):
            logger.info(f"[Celery] Skipping verified email for participation #{participation_id}: no email")
            return {'status': 'skipped', 'reason': 'no_email'}

        subject = f'[YouthHub] Xac nhan diem danh: {activity.title}'

        try:
            html_message = render_to_string('emails/attendance_verified.html', {
                'student': student,
                'activity': activity,
                'participation': participation,
            })
        except Exception:
            html_message = None

        plain_message = (
            f'Xin chao {student.get_full_name() or student.username},\n\n'
            f'Diem danh cua ban tai hoat dong "{activity.title}" da duoc xac nhan.\n'
            f'Trang thai: {participation.get_status_display() if hasattr(participation, "get_status_display") else participation.status}\n\n'
            f'Cam on ban da tham gia!\n'
            f'-- YouthHub Team'
        )

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"[Celery] Attendance verified email sent to {student.email} for activity #{activity.pk}")
        return {'status': 'sent', 'email': student.email}

    except Exception as exc:
        logger.warning(f"[Celery] Attendance email task failed for participation #{participation_id}: {exc}")
        raise self.retry(exc=exc)
