from django.contrib import admin
from .models import Activity, ActivityRegistration, Budget, BudgetItem, Task, PointCategory


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


@admin.register(ActivityRegistration)
class ActivityRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'activity', 'status', 'registered_at')
    list_filter = ('status',)


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('activity', 'total_amount', 'status')
    list_filter = ('status',)


@admin.register(BudgetItem)
class BudgetItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'budget', 'amount', 'category')
    list_filter = ('category',)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'activity', 'assigned_to', 'due_date', 'status')
    list_filter = ('status',)
    date_hierarchy = 'due_date'
