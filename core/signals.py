"""
Django Signals for Audit Logging.
Automatically log CREATE / UPDATE / DELETE on key models.
"""
from django.db.models.signals import post_save, post_delete
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .models import AuditLog


def _get_ip(request):
    """Extract client IP address from request."""
    if request is None:
        return None
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _log(user, action, instance, request=None, changes=None):
    """Helper to create an AuditLog entry."""
    log = AuditLog(
        user=user,
        action=action,
        object_type=instance.__class__.__name__,
        object_id=str(instance.pk),
        object_repr=str(instance)[:255],
        ip_address=_get_ip(request),
    )
    if changes:
        log.set_changes(changes)
    log.save()


# ─── Activity Signals ─────────────────────────────────────────────────────────

@receiver(post_save, sender='activities.Activity')
def log_activity_save(sender, instance, created, **kwargs):
    """Log when an Activity is created or updated."""
    action = AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE
    _log(
        user=instance.created_by,
        action=action,
        instance=instance,
        changes={'title': instance.title, 'status': instance.status},
    )


@receiver(post_delete, sender='activities.Activity')
def log_activity_delete(sender, instance, **kwargs):
    """Log when an Activity is deleted."""
    _log(
        user=instance.created_by,
        action=AuditLog.Action.DELETE,
        instance=instance,
        changes={'title': instance.title},
    )


# ─── Organization Signals ─────────────────────────────────────────────────────

@receiver(post_save, sender='core.Organization')
def log_org_save(sender, instance, created, **kwargs):
    action = AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE
    _log(
        user=None,
        action=action,
        instance=instance,
        changes={'name': instance.name, 'type': instance.type},
    )


@receiver(post_delete, sender='core.Organization')
def log_org_delete(sender, instance, **kwargs):
    _log(
        user=None,
        action=AuditLog.Action.DELETE,
        instance=instance,
    )


# ─── ActivityParticipation Signals ──────────────────────────────────────────────────

@receiver(post_save, sender='activities.ActivityParticipation')
def log_attendance_save(sender, instance, created, **kwargs):
    if not created:
        return
    _log(
        user=instance.student,
        action=AuditLog.Action.CREATE,
        instance=instance,
        changes={'student_code': instance.entered_student_code, 'status': instance.status},
    )


# ─── Auth Signals ─────────────────────────────────────────────────────────────

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    _log(
        user=user,
        action=AuditLog.Action.LOGIN,
        instance=user,
        request=request,
        changes={'username': user.username},
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user:
        _log(
            user=user,
            action=AuditLog.Action.LOGOUT,
            instance=user,
            request=request,
        )
