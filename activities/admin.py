from django.contrib import admin
from .models import Activity, ActivityParticipation, PointCategory


@admin.register(PointCategory)
class PointCategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    ordering = ['code']


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'organization', 'activity_type', 'point_category', 'status', 'start_time')
    list_filter = ('status', 'activity_type', 'semester', 'point_category')
    search_fields = ('title', 'code')
    date_hierarchy = 'start_time'


@admin.register(ActivityParticipation)
class ActivityParticipationAdmin(admin.ModelAdmin):
    list_display = ('student', 'entered_student_code', 'activity', 'status', 'registered_at')
    list_filter = ('status',)
