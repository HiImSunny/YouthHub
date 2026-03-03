from django.contrib import admin
from .models import AttendanceSession, AttendanceRecord, ActivityPoint


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('activity', 'name', 'status', 'requires_photo', 'start_time')
    list_filter = ('status', 'requires_photo')


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('entered_student_code', 'attendance_session', 'status', 'checkin_time')
    list_filter = ('status',)
    search_fields = ('entered_student_code',)


@admin.register(ActivityPoint)
class ActivityPointAdmin(admin.ModelAdmin):
    list_display = ('student', 'activity', 'points', 'reason', 'created_at')
    list_filter = ('reason',)
