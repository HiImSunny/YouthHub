from django.contrib import admin
from .models import AttendanceSession


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('activity', 'name', 'status', 'requires_photo', 'start_time')
    list_filter = ('status', 'requires_photo')
