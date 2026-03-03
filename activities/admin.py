from django.contrib import admin
from .models import Activity, ActivityRegistration, Budget, BudgetItem, Task


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'organization', 'activity_type', 'status', 'start_time')
    list_filter = ('status', 'activity_type', 'semester')
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
